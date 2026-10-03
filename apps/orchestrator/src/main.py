import json
import os
import re
import sqlite3
from html import unescape
from pathlib import Path
from typing import Literal
from urllib import error as urllib_error
from urllib import request as urllib_request
from uuid import uuid4

from dotenv import load_dotenv

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - optional dependency for PDF ingestion
    PdfReader = None

try:
    import psycopg
except ImportError:  # pragma: no cover - optional dependency for Postgres-backed knowledge
    psycopg = None

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

try:
    from .approved_source_connector import build_source_record, collect_approved_sources_from_directory
except ImportError:  # pragma: no cover - fallback for direct script execution
    from approved_source_connector import build_source_record, collect_approved_sources_from_directory


class CompatResponse:
    def __init__(self, inner_response):
        self._inner = inner_response

    @property
    def status_code(self):
        return self._inner.status_code

    def get_json(self):
        return self._inner.json()

    def json(self):
        return self._inner.json()

    def __getattr__(self, name):
        return getattr(self._inner, name)


class CompatTestClient:
    def __init__(self, fastapi_app):
        self._client = TestClient(fastapi_app)

    def __getattr__(self, name):
        return getattr(self._client, name)

    def get(self, *args, **kwargs):
        return CompatResponse(self._client.get(*args, **kwargs))

    def post(self, *args, **kwargs):
        return CompatResponse(self._client.post(*args, **kwargs))

    def put(self, *args, **kwargs):
        return CompatResponse(self._client.put(*args, **kwargs))

    def patch(self, *args, **kwargs):
        return CompatResponse(self._client.patch(*args, **kwargs))

    def delete(self, *args, **kwargs):
        return CompatResponse(self._client.delete(*args, **kwargs))


app = FastAPI(title="AMANI Orchestrator", version="0.1.0")
app.test_client = lambda: CompatTestClient(app)

PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", str(Path(__file__).resolve().parents[3]) if len(Path(__file__).resolve().parents) > 3 else "/app"))
load_dotenv(PROJECT_ROOT / ".env")
DATA_DIR = Path(os.getenv("AMANI_DATA_DIR", str(PROJECT_ROOT / "data")))
DB_PATH = Path(os.getenv("AMANI_LEGACY_DB", str(DATA_DIR / "amani_line.db")))
DATABASE_URL = os.getenv("DATABASE_URL")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "20"))

try:
    from .support import install as install_support
except ImportError:
    from support import install as install_support
install_support(app)


def extract_pdf_text(pdf_path: str | Path) -> str:
    file_path = Path(pdf_path)
    if not file_path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    if PdfReader is None:
        raise ImportError("pypdf is required to extract PDF content.")

    reader = PdfReader(str(file_path))
    text_parts: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            text_parts.append(page_text.strip())

    return "\n\n".join(text_parts).strip()


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + chunk_size)
        chunk = cleaned[start:end].strip()
        if not chunk:
            break
        chunks.append(chunk)
        if end >= len(cleaned):
            break
        start = max(start + chunk_size - overlap, end - overlap)
    return chunks


def ingest_pdf_document(pdf_path: str | Path, source_name: str = "Uploaded PDF", category: str = "general") -> dict:
    file_path = Path(pdf_path)
    extracted = extract_pdf_text(file_path)
    chunks = chunk_text(extracted)
    summary = chunks[0][:500] if chunks else extracted[:500]
    title = file_path.stem.replace("_", " ").strip() or source_name

    review = create_source_review({
        "id": f"pdf-review-{uuid4().hex[:12]}",
        "title": title,
        "summary": summary,
        "category": category,
        "source": source_name,
        "source_url": str(file_path),
        "verified_at": "pending-review",
        "tags": "pdf, source-document, review-needed",
        "notes": f"{len(chunks)} extracted text chunks ready for review.",
    })
    return review


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    channel: Literal["web", "whatsapp"] = "web"
    region: str | None = None
    sessionId: str | None = None


class ChatResponse(BaseModel):
    reply: str
    pillar: str
    triage: Literal["routine", "urgent", "priority-handoff"]
    escalationNeeded: bool
    suggestions: list[str]


class CaseUpdateRequest(BaseModel):
    status: Literal["queued", "in_progress", "resolved"] | None = None
    priority: Literal["critical", "high", "medium"] | None = None
    assignee: str | None = None
    notes: str | None = None


APPROVED_REFERRALS = {
    "protest-rights": {
        "reply": "You can ask about arrest procedures, police conduct, and what support is available in Ghana. I can connect you to a verified legal aid or rights defender resource if you want.",
        "suggestions": ["View legal aid contacts", "Find a local rights organisation", "Talk to a human moderator"],
    },
    "digital-rights": {
        "reply": "For online safety, harassment, phishing, or account compromise, start by preserving evidence and changing passwords on the affected accounts. I can help you find a digital security contact or report a harmful link.",
        "suggestions": ["Check a suspicious link", "Find digital security help", "Report harassment"],
    },
    "mental-health": {
        "reply": "If you or someone else may be in immediate danger, please contact emergency services or a trusted person now. I can also connect you to a mental health support line that can help you stay safe.",
        "suggestions": ["Call a crisis line", "Find a counsellor", "Talk to a human support worker"],
    },
    "gender-rights": {
        "reply": "You deserve safety, respect, and confidential support. I can help you find local GBV support, legal assistance, or a safe contact for follow-up.",
        "suggestions": ["Find GBV support", "Look up legal aid", "Speak with an advocate"],
    },
}

REFERRAL_DIRECTORY = [
    {
        "id": "gbv-support",
        "title": "Confidential GBV Support",
        "organisation": "AMANI partner network",
        "phone": "Available through moderator desk",
        "website": "Moderator referral channel",
        "notes": "Safe, confidential support for gender-based violence and survivor care coordination.",
    },
    {
        "id": "legal-aid",
        "title": "Legal Aid & Rights Advice",
        "organisation": "Rights defence partners",
        "phone": "Available through moderator desk",
        "website": "Moderator referral channel",
        "notes": "Support for arrest procedures, civic rights, online safety, and legal follow-up.",
    },
    {
        "id": "mental-health",
        "title": "Mental Health & Crisis Support",
        "organisation": "Wellbeing support partners",
        "phone": "Available through moderator desk",
        "website": "Moderator referral channel",
        "notes": "Immediate wellbeing support and crisis planning for youth and families.",
    },
]

KNOWLEDGE_ARTICLES = [
    {
        "id": "ghana-mental-health-authority",
        "title": "Ghana Mental Health Authority",
        "summary": "Official guidance and crisis support pathways for mental health, distress, and wellbeing support in Ghana.",
        "category": "mental-health",
        "source": "Ghana Mental Health Authority",
        "source_url": "https://mha.gov.gh/",
        "verified_at": "2026-09-10",
        "tags": "mental health, crisis, wellbeing, ghana",
    },
    {
        "id": "chraj-rights-guide",
        "title": "CHRAJ rights guidance",
        "summary": "Rights-based guidance for civic freedoms, detention concerns, and how to find legal or human-rights support in Ghana.",
        "category": "protest-rights",
        "source": "CHRAJ",
        "source_url": "https://chraj.gov.gh/",
        "verified_at": "2026-09-10",
        "tags": "rights, civic freedom, detention, legal aid, ghana",
    },
    {
        "id": "digital-security-basics",
        "title": "Digital security basics",
        "summary": "Practical steps for preserving evidence, changing passwords, and avoiding phishing and online harassment.",
        "category": "digital-rights",
        "source": "Digital safety referral network",
        "source_url": "https://www.amnesty.org/en/tech/",
        "verified_at": "2026-09-10",
        "tags": "digital rights, online safety, phishing, evidence, security",
    },
    {
        "id": "gbv-support-guide",
        "title": "Gender-based violence support pathways",
        "summary": "Confidential support, safety planning, and referral options for survivors and people seeking GBV help.",
        "category": "gender-rights",
        "source": "AMANI partner network",
        "source_url": "https://www.unwomen.org/en",
        "verified_at": "2026-09-10",
        "tags": "gbv, gender rights, safety, survivor support",
    },
]

TRUSTED_SOURCES = [
    {
        "id": "amnesty-international",
        "name": "Amnesty International",
        "domain": "amnesty.org",
        "url": "https://www.amnesty.org/en/tech/",
        "category": "digital-rights",
        "notes": "Trusted source for digital rights, online safety, and rights-based guidance.",
    },
    {
        "id": "chraj",
        "name": "CHRAJ",
        "domain": "chraj.gov.gh",
        "url": "https://chraj.gov.gh/",
        "category": "protest-rights",
        "notes": "Official Ghana rights and legal aid guidance source.",
    },
    {
        "id": "ghana-mental-health-authority",
        "name": "Ghana Mental Health Authority",
        "domain": "mha.gov.gh",
        "url": "https://mha.gov.gh/",
        "category": "mental-health",
        "notes": "Official Ghana mental health and crisis support source.",
    },
    {
        "id": "unwomen",
        "name": "UN Women",
        "domain": "unwomen.org",
        "url": "https://www.unwomen.org/en",
        "category": "gender-rights",
        "notes": "Trusted global guidance for GBV and survivor support.",
    },
]

URGENT_KEYWORDS = [
    "self-harm",
    "suicide",
    "hurt myself",
    "kill myself",
    "trafficking",
    "imminent danger",
    "may hurt",
    "arrest in progress",
    "being followed",
    "threat of violence",
]

PILLAR_KEYWORDS = {
    "protest-rights": [
        "arrest",
        "detained",
        "police",
        "rights",
        "protest",
        "march",
        "demonstration",
        "legal aid",
        "civic",
        "lawyer",
        "detention",
    ],
    "digital-rights": [
        "phishing",
        "online safety",
        "harassment",
        "scam",
        "account",
        "password",
        "hacked",
        "suspicious link",
        "social media",
        "online",
        "abuse online",
        "report",
        "blocked",
    ],
    "mental-health": [
        "anxiety",
        "panic",
        "depressed",
        "depression",
        "stress",
        "overwhelmed",
        "mental health",
        "crying",
        "not okay",
        "unsafe",
        "crisis",
        "suicide",
    ],
    "gender-rights": [
        "gbv",
        "abuse",
        "assault",
        "unsafe",
        "domestic",
        "partner",
        "sexual",
        "survivor",
        "violence",
        "harassed",
        "gender",
        "discrimination",
    ],
}


def initialize_database() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            channel TEXT,
            message TEXT,
            reply TEXT,
            pillar TEXT,
            triage TEXT,
            escalation_needed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS moderator_cases (
            id TEXT PRIMARY KEY,
            title TEXT,
            channel TEXT,
            summary TEXT,
            priority TEXT,
            status TEXT,
            assignee TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS referrals (
            id TEXT PRIMARY KEY,
            title TEXT,
            organisation TEXT,
            phone TEXT,
            website TEXT,
            notes TEXT
        )
        """
    )

    moderator_case_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(moderator_cases)").fetchall()
    }
    if "assignee" not in moderator_case_columns:
        conn.execute("ALTER TABLE moderator_cases ADD COLUMN assignee TEXT")
    if "notes" not in moderator_case_columns:
        conn.execute("ALTER TABLE moderator_cases ADD COLUMN notes TEXT")
    if "updated_at" not in moderator_case_columns:
        conn.execute("ALTER TABLE moderator_cases ADD COLUMN updated_at TEXT")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS knowledge_articles (
            id TEXT PRIMARY KEY,
            title TEXT,
            summary TEXT,
            category TEXT,
            source TEXT,
            source_url TEXT,
            verified_at TEXT,
            tags TEXT
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS trusted_sources (
            id TEXT PRIMARY KEY,
            name TEXT,
            domain TEXT,
            url TEXT,
            category TEXT,
            notes TEXT,
            trust_score INTEGER DEFAULT 0
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS source_reviews (
            id TEXT PRIMARY KEY,
            title TEXT,
            summary TEXT,
            category TEXT,
            source TEXT,
            source_url TEXT,
            verified_at TEXT,
            tags TEXT,
            status TEXT DEFAULT 'pending',
            reviewer TEXT,
            reviewed_at TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS review_history (
            id TEXT PRIMARY KEY,
            review_id TEXT,
            status TEXT,
            reviewer TEXT,
            notes TEXT,
            changed_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    trusted_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(trusted_sources)").fetchall()
    }
    if "trust_score" not in trusted_columns:
        conn.execute("ALTER TABLE trusted_sources ADD COLUMN trust_score INTEGER DEFAULT 0")

    knowledge_columns = {
        row[1] for row in conn.execute("PRAGMA table_info(knowledge_articles)").fetchall()
    }
    if "source_url" not in knowledge_columns:
        conn.execute("ALTER TABLE knowledge_articles ADD COLUMN source_url TEXT")

    conn.executemany(
        """
        INSERT OR IGNORE INTO referrals (id, title, organisation, phone, website, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                item["id"],
                item["title"],
                item["organisation"],
                item["phone"],
                item["website"],
                item["notes"],
            )
            for item in REFERRAL_DIRECTORY
        ],
    )

    conn.executemany(
        """
        INSERT OR IGNORE INTO knowledge_articles (id, title, summary, category, source, source_url, verified_at, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                item["id"],
                item["title"],
                item["summary"],
                item["category"],
                item["source"],
                item.get("source_url"),
                item["verified_at"],
                item["tags"],
            )
            for item in KNOWLEDGE_ARTICLES
        ],
    )

    conn.executemany(
        """
        INSERT OR IGNORE INTO trusted_sources (id, name, domain, url, category, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                item["id"],
                item["name"],
                item["domain"],
                item["url"],
                item["category"],
                item["notes"],
            )
            for item in TRUSTED_SOURCES
        ],
    )

    conn.commit()
    conn.close()


def initialize_postgres_seed_data() -> None:
    if not DATABASE_URL or psycopg is None:
        return

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS referrals (
                        id TEXT PRIMARY KEY,
                        title TEXT,
                        organisation TEXT,
                        phone TEXT,
                        website TEXT,
                        notes TEXT
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS knowledge_articles (
                        id TEXT PRIMARY KEY,
                        title TEXT,
                        summary TEXT,
                        category TEXT,
                        source TEXT,
                        source_url TEXT,
                        verified_at TEXT,
                        tags TEXT
                    )
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS trusted_sources (
                        id TEXT PRIMARY KEY,
                        name TEXT,
                        domain TEXT,
                        url TEXT,
                        category TEXT,
                        notes TEXT
                    )
                    """
                )
                try:
                    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                except Exception:
                    pass
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS knowledge_embeddings (
                        article_id TEXT PRIMARY KEY,
                        embedding VECTOR(1536)
                    )
                    """
                )
                cur.executemany(
                    """
                    INSERT INTO referrals (id, title, organisation, phone, website, notes)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    [
                        (
                            item["id"],
                            item["title"],
                            item["organisation"],
                            item["phone"],
                            item["website"],
                            item["notes"],
                        )
                        for item in REFERRAL_DIRECTORY
                    ],
                )
                cur.executemany(
                    """
                    INSERT INTO knowledge_articles (id, title, summary, category, source, source_url, verified_at, tags)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    [
                        (
                            item["id"],
                            item["title"],
                            item["summary"],
                            item["category"],
                            item["source"],
                            item.get("source_url"),
                            item["verified_at"],
                            item["tags"],
                        )
                        for item in KNOWLEDGE_ARTICLES
                    ],
                )
                cur.executemany(
                    """
                    INSERT INTO trusted_sources (id, name, domain, url, category, notes)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    [
                        (
                            item["id"],
                            item["name"],
                            item["domain"],
                            item["url"],
                            item["category"],
                            item["notes"],
                        )
                        for item in TRUSTED_SOURCES
                    ],
                )
                conn.commit()
    except Exception:
        return

    sync_postgres_embeddings()


def save_chat_record(
    session_id: str | None,
    channel: str,
    message: str,
    reply: str,
    pillar: str,
    triage: str,
    escalation_needed: bool,
) -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO chats (session_id, channel, message, reply, pillar, triage, escalation_needed)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (session_id, channel, message, reply, pillar, triage, int(escalation_needed)),
    )
    conn.commit()
    conn.close()


def create_case_record(message: str, channel: str) -> str:
    case_id = f"A-{uuid4().hex[:8].upper()}"
    priority = (
        "critical"
        if any(keyword in message.lower() for keyword in ["self-harm", "suicide", "hurt myself", "kill myself"])
        else "high"
    )

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO moderator_cases (id, title, channel, summary, priority, status, assignee, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            case_id,
            "Urgent support handoff",
            channel,
            f"Escalated case created from user message: {message}",
            priority,
            "queued",
            None,
            None,
        ),
    )
    conn.commit()
    conn.close()
    return case_id


def _rows_to_dicts(columns, rows):
    return [dict(zip(columns, row)) for row in rows]


def _get_source_trust_score(source_name: str | None, source_url: str | None = None) -> int:
    source_value = (source_name or "").strip()
    url_value = (source_url or "").strip()
    if not source_value and not url_value:
        return 0

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT trust_score FROM trusted_sources WHERE name = ? OR url = ? ORDER BY trust_score DESC LIMIT 1",
        (source_value, url_value),
    ).fetchone()
    conn.close()
    if row is None:
        return 0
    return int(row["trust_score"] or 0)


def score_knowledge_match(article: dict, query: str) -> int:
    stripped_query = query.strip().lower()
    if not stripped_query:
        return 0

    title = (article.get("title") or "").lower()
    summary = (article.get("summary") or "").lower()
    category = (article.get("category") or "").lower()
    source = (article.get("source") or "").lower()
    tags = (article.get("tags") or "").lower()
    source_url = (article.get("source_url") or "").lower()

    score = 0
    query_terms = [term for term in stripped_query.split() if len(term) >= 3]

    category_boost = 0
    if category and any(term in category for term in query_terms):
        category_boost += 18
    if any(term in title for term in query_terms):
        category_boost += 8
    if any(term in summary for term in query_terms):
        category_boost += 6
    if any(term in tags for term in query_terms):
        category_boost += 6
    if any(term in source for term in query_terms):
        category_boost += 4

    score += category_boost

    if stripped_query in title:
        score += 12
    if stripped_query in summary:
        score += 8
    if stripped_query in tags:
        score += 8
    if stripped_query in source:
        score += 4
    if stripped_query in source_url:
        score += 3

    for term in query_terms:
        if term in title:
            score += 5
        if term in summary:
            score += 3
        if term in category:
            score += 6
        if term in tags:
            score += 4
        if term in source:
            score += 2
        if term in source_url:
            score += 1

    if category in {"mental-health", "digital-rights", "gender-rights", "protest-rights"}:
        score += 10

    trust_score = _get_source_trust_score(article.get("source"), article.get("source_url"))
    source_bonus = trust_score // 2
    score += source_bonus

    mental_health_query = any(term in ["depressed", "depression", "stress", "overwhelmed", "panic", "anxiety", "mental health"] for term in query_terms)
    if category == "mental-health" and mental_health_query:
        score += 30
    elif category and category != "mental-health" and mental_health_query:
        score -= 25
    if category == "digital-rights" and any(term in ["online", "account", "password", "phishing", "harassment", "hack", "suspicious"] for term in query_terms):
        score += 20
    if category == "protest-rights" and any(term in ["police", "arrest", "legal", "rights", "detained", "protest"] for term in query_terms):
        score += 18
    if "category" in article and article.get("category") == "mental-health" and category == "mental-health":
        score += 8

    return score


def fetch_trusted_sources() -> list[dict]:
    if DATABASE_URL and psycopg is not None:
        try:
            with psycopg.connect(DATABASE_URL) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM trusted_sources ORDER BY name")
                    rows = cur.fetchall()
                    columns = [desc[0] for desc in cur.description]
                    return _rows_to_dicts(columns, rows)
        except Exception:
            pass

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM trusted_sources ORDER BY name"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def _extract_html_text(value: str | None) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"<script.*?</script>", " ", value, flags=re.I | re.S)
    cleaned = re.sub(r"<style.*?</style>", " ", cleaned, flags=re.I | re.S)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = unescape(cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _fetch_source_url_metadata(source_url: str | None) -> dict:
    if not source_url:
        return {}

    try:
        request = urllib_request.Request(
            source_url,
            headers={"User-Agent": "AmaniLineBot/1.0"},
        )
        with urllib_request.urlopen(request, timeout=10) as response:
            payload = response.read().decode("utf-8", errors="ignore")
    except Exception:
        return {}

    title_match = re.search(r"<title[^>]*>(.*?)</title>", payload, flags=re.I | re.S)
    title = unescape(re.sub(r"\s+", " ", title_match.group(1)).strip()) if title_match else ""

    description_match = re.search(
        r"<meta[^>]+(?:name|property)=['\"](?:description|og:description)['\"][^>]*content=['\"]([^'\"]+)['\"]",
        payload,
        flags=re.I | re.S,
    )
    description = unescape(re.sub(r"\s+", " ", description_match.group(1)).strip()) if description_match else ""

    if not description:
        first_paragraph = re.search(r"<p[^>]*>(.*?)</p>", payload, flags=re.I | re.S)
        if first_paragraph:
            description = _extract_html_text(first_paragraph.group(1))

    return {"title": title, "summary": description}


def ingest_approved_sources(sources: list[dict]) -> list[dict]:
    ingested: list[dict] = []
    for source in sources:
        if not isinstance(source, dict):
            continue

        content_path = source.get("content_path")
        summary = (source.get("summary") or "").strip()
        title = (source.get("title") or "Untitled approved source").strip()
        source_url = (source.get("source_url") or "").strip()

        if content_path:
            try:
                with Path(content_path).open("r", encoding="utf-8") as handle:
                    content_text = handle.read().strip()
                if content_text and not summary:
                    summary = content_text[:500]
                if content_text and title == "Untitled approved source":
                    title = Path(content_path).stem.replace("_", " ").title()
            except Exception:
                pass

        if source_url and (title == "Untitled approved source" or not summary):
            metadata = _fetch_source_url_metadata(source_url)
            if metadata.get("title") and title == "Untitled approved source":
                title = metadata["title"]
            if metadata.get("summary") and not summary:
                summary = metadata["summary"]

        if not title or title == "Untitled approved source":
            fallback = build_source_record(
                file_path=content_path,
                url=source_url,
                source_name=source.get("source") or "Approved external source",
                category=source.get("category") or "general",
                source_url=source_url,
                tags=source.get("tags") or "approved-source, review-needed",
                title=title if title and title != "Untitled approved source" else None,
                summary=summary or None,
            )
            title = fallback["title"]
            summary = fallback["summary"]

        review = create_source_review({
            "id": source.get("id"),
            "title": title,
            "summary": summary,
            "category": source.get("category") or "general",
            "source": source.get("source") or "Approved external source",
            "source_url": source_url,
            "verified_at": source.get("verified_at") or "pending-review",
            "tags": source.get("tags") or "approved-source, review-needed",
            "notes": source.get("notes") or "Imported via approved-source intake pipeline.",
        })
        ingested.append(review)

    return ingested


def ingest_approved_sources_from_directory(
    directory: str | Path,
    *,
    source_name: str = "Approved source",
    category: str = "general",
    source_url_prefix: str | None = None,
    tags: str | None = None,
) -> list[dict]:
    sources = collect_approved_sources_from_directory(
        directory,
        source_name=source_name,
        category=category,
        source_url_prefix=source_url_prefix,
        tags=tags,
    )
    return ingest_approved_sources(sources)


def create_source_review(submission: dict) -> dict:
    article = {
        "id": submission.get("id") or f"review-{uuid4().hex[:12]}",
        "title": submission.get("title") or "Untitled source review",
        "summary": submission.get("summary") or "",
        "category": submission.get("category") or "general",
        "source": submission.get("source") or "Unknown source",
        "source_url": submission.get("source_url") or "",
        "verified_at": submission.get("verified_at") or "unknown",
        "tags": submission.get("tags") or "",
    }

    record = {
        **article,
        "status": "pending",
        "reviewer": None,
        "reviewed_at": None,
        "notes": submission.get("notes") or "",
    }

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO source_reviews (id, title, summary, category, source, source_url, verified_at, tags, status, reviewer, reviewed_at, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record["id"],
            record["title"],
            record["summary"],
            record["category"],
            record["source"],
            record["source_url"],
            record["verified_at"],
            record["tags"],
            record["status"],
            record["reviewer"],
            record["reviewed_at"],
            record["notes"],
        ),
    )
    conn.commit()
    conn.close()
    return record


def fetch_review_queue(status: str | None = None) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    query = "SELECT * FROM source_reviews"
    params: list[str] = []
    if status and status.strip():
        query += " WHERE status = ?"
        params.append(status.strip())

    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def _record_review_history(review_id: str, status: str, reviewer: str | None, notes: str | None) -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS review_history (
            id TEXT PRIMARY KEY,
            review_id TEXT,
            status TEXT,
            reviewer TEXT,
            notes TEXT,
            changed_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
    )
    conn.execute(
        """
        INSERT INTO review_history (id, review_id, status, reviewer, notes)
        VALUES (?, ?, ?, ?, ?)
        """,
        (f"history-{uuid4().hex[:12]}", review_id, status, reviewer or "moderator", notes or ""),
    )
    conn.commit()
    conn.close()


def fetch_review_history(review_id: str | None = None) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    query = "SELECT * FROM review_history"
    params: list[str] = []
    if review_id:
        query += " WHERE review_id = ?"
        params.append(review_id)
    query += " ORDER BY changed_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def _default_trust_score(source_name: str, source_url: str | None = None) -> int:
    name_lower = (source_name or "").lower()
    url_lower = (source_url or "").lower()

    if any(marker in name_lower for marker in ["amani", "amnesty", "chraj", "ghana", "authority", "un women", "unwomen", "government", "ministry", "official"]):
        return 90
    if any(marker in url_lower for marker in ["gov.gh", "amnesty.org", "unwomen.org", "who.int", "who"]):
        return 85
    if any(marker in name_lower for marker in ["community", "blog", "local", "tips", "desk"]):
        return 50
    return 60


def _sync_source_trust_record(source_name: str, source_url: str, category: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    name = source_name.strip() or "Unknown source"
    domain = ""
    if source_url:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(source_url)
            domain = parsed.netloc or ""
        except Exception:
            domain = ""

    if source_url:
        existing = conn.execute(
            "SELECT * FROM trusted_sources WHERE name = ? AND url = ?",
            (name, source_url),
        ).fetchone()
    else:
        existing = conn.execute(
            "SELECT * FROM trusted_sources WHERE name = ?",
            (name,),
        ).fetchone()

    if existing is None:
        trust_score = _default_trust_score(name, source_url)
        record = {
            "id": f"source-{uuid4().hex[:8]}",
            "name": name,
            "domain": domain,
            "url": source_url or "",
            "category": category,
            "notes": "Reviewed and approved for live publication.",
            "trust_score": trust_score,
        }
        conn.execute(
            """
            INSERT INTO trusted_sources (id, name, domain, url, category, notes, trust_score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (record["id"], record["name"], record["domain"], record["url"], record["category"], record["notes"], record["trust_score"]),
        )
    else:
        current_score = int(dict(existing).get("trust_score") or 0)
        baseline_score = _default_trust_score(name, source_url)

        if baseline_score >= 80:
            new_score = max(baseline_score, min(100, max(current_score, baseline_score)))
        else:
            new_score = baseline_score

        conn.execute(
            "UPDATE trusted_sources SET trust_score = ?, category = COALESCE(?, category), url = COALESCE(?, url), notes = COALESCE(?, notes) WHERE id = ?",
            (new_score, category or None, source_url or None, "Reviewed and approved for live publication.", existing["id"]),
        )
        record = {**dict(existing), "trust_score": new_score}

    conn.commit()
    conn.close()
    return record


def reject_source_review(review_id: str, reviewer: str | None = None, notes: str | None = None) -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM source_reviews WHERE id = ?", (review_id,)).fetchone()
    if row is None:
        conn.close()
        raise ValueError(f"Source review {review_id} was not found.")

    review = dict(row)
    review["status"] = "rejected"
    review["reviewer"] = reviewer or "moderator"
    review["reviewed_at"] = "CURRENT_TIMESTAMP"
    review["notes"] = notes or review.get("notes") or ""

    conn.execute(
        """
        UPDATE source_reviews
        SET status = ?, reviewer = ?, reviewed_at = ?, notes = ?
        WHERE id = ?
        """,
        (review["status"], review["reviewer"], review["reviewed_at"], review["notes"], review_id),
    )
    conn.commit()
    conn.close()
    _record_review_history(review_id, review["status"], review["reviewer"], review["notes"])
    return review


def approve_source_review(review_id: str, reviewer: str | None = None, notes: str | None = None) -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM source_reviews WHERE id = ?", (review_id,)).fetchone()
    if row is None:
        conn.close()
        raise ValueError(f"Source review {review_id} was not found.")

    review = dict(row)
    review["status"] = "approved"
    review["reviewer"] = reviewer or "moderator"
    review["reviewed_at"] = "CURRENT_TIMESTAMP"
    review["notes"] = notes or review.get("notes") or ""

    conn.execute(
        """
        UPDATE source_reviews
        SET status = ?, reviewer = ?, reviewed_at = ?, notes = ?
        WHERE id = ?
        """,
        (review["status"], review["reviewer"], review["reviewed_at"], review["notes"], review_id),
    )
    conn.commit()
    conn.close()
    _record_review_history(review_id, review["status"], review["reviewer"], review["notes"])

    article = {
        "id": review_id,
        "title": review["title"],
        "summary": review["summary"],
        "category": review["category"],
        "source": review["source"],
        "source_url": review["source_url"],
        "verified_at": review["verified_at"],
        "tags": review["tags"],
    }
    _sync_source_trust_record(review["source"], review["source_url"], review["category"])
    upsert_knowledge_article(article)
    return review


def publish_approved_review(review_id: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM source_reviews WHERE id = ?", (review_id,)).fetchone()
    if row is None:
        conn.close()
        raise ValueError(f"Source review {review_id} was not found.")

    review = dict(row)
    if review.get("status") != "approved":
        conn.close()
        raise ValueError(f"Source review {review_id} is not approved for publication.")

    article = {
        "id": review_id,
        "title": review["title"],
        "summary": review["summary"],
        "category": review["category"],
        "source": review["source"],
        "source_url": review["source_url"],
        "verified_at": review["verified_at"],
        "tags": review["tags"],
    }
    saved = upsert_knowledge_article(article)

    chunks = review.get("notes", "").split("\n") if review.get("notes") else []
    if not chunks and review.get("summary"):
        chunks = [review["summary"]]

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS review_chunks (
            id TEXT PRIMARY KEY,
            review_id TEXT,
            chunk_text TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
    )

    for index, chunk in enumerate(chunks, start=1):
        if not chunk or not chunk.strip():
            continue
        chunk_id = f"{review_id}-chunk-{index}"
        conn.execute(
            "INSERT OR REPLACE INTO review_chunks (id, review_id, chunk_text) VALUES (?, ?, ?)",
            (chunk_id, review_id, chunk.strip()),
        )

    conn.execute(
        "UPDATE source_reviews SET status = ? WHERE id = ?",
        ("published", review_id),
    )
    conn.commit()
    conn.close()
    _record_review_history(review_id, "published", "moderator", "Published to live knowledge store.")
    _sync_source_trust_record(review["source"], review["source_url"], review["category"])
    return {"id": review_id, "status": "published", "article": saved}


def upsert_knowledge_article(article: dict) -> dict:
    normalized = {
        "id": article.get("id") or article.get("title", "").strip().lower().replace(" ", "-")
        ,
        "title": article.get("title") or "Untitled source",
        "summary": article.get("summary") or "",
        "category": article.get("category") or "general",
        "source": article.get("source") or "Unknown source",
        "source_url": article.get("source_url") or "",
        "verified_at": article.get("verified_at") or "unknown",
        "tags": article.get("tags") or "",
    }

    if DATABASE_URL and psycopg is not None:
        try:
            with psycopg.connect(DATABASE_URL) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO knowledge_articles (id, title, summary, category, source, source_url, verified_at, tags)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE
                        SET title = EXCLUDED.title,
                            summary = EXCLUDED.summary,
                            category = EXCLUDED.category,
                            source = EXCLUDED.source,
                            source_url = EXCLUDED.source_url,
                            verified_at = EXCLUDED.verified_at,
                            tags = EXCLUDED.tags
                        """,
                        (
                            normalized["id"],
                            normalized["title"],
                            normalized["summary"],
                            normalized["category"],
                            normalized["source"],
                            normalized["source_url"],
                            normalized["verified_at"],
                            normalized["tags"],
                        ),
                    )
                    conn.commit()
                    content = " ".join(part for part in [normalized["title"], normalized["summary"], normalized["tags"]] if part)
                    embedding = generate_embedding(content)
                    if embedding:
                        embedding_value = "[" + ",".join(f"{value:.6f}" for value in embedding) + "]"
                        cur.execute(
                            """
                            INSERT INTO knowledge_embeddings (article_id, embedding)
                            VALUES (%s, %s::vector)
                            ON CONFLICT (article_id) DO UPDATE SET embedding = EXCLUDED.embedding
                            """,
                            (normalized["id"], embedding_value),
                        )
                        conn.commit()
                    return normalized
        except Exception:
            pass

    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO knowledge_articles (id, title, summary, category, source, source_url, verified_at, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalized["id"],
                normalized["title"],
                normalized["summary"],
                normalized["category"],
                normalized["source"],
                normalized["source_url"],
                normalized["verified_at"],
                normalized["tags"],
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return normalized


def batch_ingest_knowledge_articles(articles: list[dict]) -> list[dict]:
    saved: list[dict] = []
    for article in articles:
        saved.append(upsert_knowledge_article(article))
    return saved


def generate_embedding(text: str) -> list[float] | None:
    stripped = text.strip()
    if not OPENAI_API_KEY or not stripped:
        return None

    endpoint = f"{OPENAI_BASE_URL.rstrip('/')}/embeddings"
    payload = {
        "model": OPENAI_EMBEDDING_MODEL,
        "input": stripped,
    }
    request = urllib_request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib_request.urlopen(request, timeout=LLM_TIMEOUT) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None

    try:
        embedding = response_data["data"][0]["embedding"]
        return [float(value) for value in embedding]
    except Exception:
        return None


def sync_postgres_embeddings() -> None:
    if not DATABASE_URL or psycopg is None:
        return

    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                except Exception:
                    return

                try:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS knowledge_embeddings (
                            article_id TEXT PRIMARY KEY,
                            embedding VECTOR(1536)
                        )
                        """
                    )
                except Exception:
                    return

                cur.execute("SELECT id, title, summary, tags FROM knowledge_articles ORDER BY id")
                rows = cur.fetchall()
                for article_id, title, summary, tags in rows:
                    cur.execute(
                        "SELECT 1 FROM knowledge_embeddings WHERE article_id = %s",
                        (article_id,),
                    )
                    if cur.fetchone() is not None:
                        continue

                    content = " ".join(part for part in [title, summary, tags] if part)
                    embedding = generate_embedding(content)
                    if not embedding:
                        continue

                    embedding_value = "[" + ",".join(f"{value:.6f}" for value in embedding) + "]"
                    cur.execute(
                        """
                        INSERT INTO knowledge_embeddings (article_id, embedding)
                        VALUES (%s, %s::vector)
                        """,
                        (article_id, embedding_value),
                    )
                conn.commit()
    except Exception:
        return


def fetch_cases(
    status: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
    search: str | None = None,
) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    query = "SELECT * FROM moderator_cases"
    conditions: list[str] = []
    params: list[str] = []

    if status:
        conditions.append("status = ?")
        params.append(status)
    if priority:
        conditions.append("priority = ?")
        params.append(priority)
    if assignee:
        conditions.append("assignee = ?")
        params.append(assignee)
    if search and search.strip():
        search_term = f"%{search.strip().lower()}%"
        conditions.append("(LOWER(title) LIKE ? OR LOWER(summary) LIKE ? OR LOWER(notes) LIKE ?)")
        params.extend([search_term, search_term, search_term])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY created_at DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def fetch_referrals() -> list[dict]:
    if DATABASE_URL and psycopg is not None:
        try:
            with psycopg.connect(DATABASE_URL) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM referrals ORDER BY id")
                    rows = cur.fetchall()
                    columns = [desc[0] for desc in cur.description]
                    return _rows_to_dicts(columns, rows)
        except Exception:
            pass

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM referrals ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def _deduplicate_knowledge_articles(articles: list[dict]) -> list[dict]:
    deduped: dict[tuple[str, str], dict] = {}
    for article in articles:
        title = (article.get("title") or "").strip().lower()
        source = (article.get("source") or "").strip().lower()
        source_url = (article.get("source_url") or "").strip().lower()
        key = (title, source_url or source)
        current = deduped.get(key)
        if current is None:
            deduped[key] = article
            continue
        current_score = _get_source_trust_score(current.get("source"), current.get("source_url"))
        article_score = _get_source_trust_score(article.get("source"), article.get("source_url"))
        if article_score > current_score:
            deduped[key] = article
    return list(deduped.values())


def fetch_knowledge_articles(query: str | None = None, limit: int = 5) -> list[dict]:
    if DATABASE_URL and psycopg is not None:
        try:
            with psycopg.connect(DATABASE_URL) as conn:
                with conn.cursor() as cur:
                    query_text = query.strip() if query else ""

                    if query_text:
                        embedding = generate_embedding(query_text)
                        if embedding:
                            embedding_value = "[" + ",".join(f"{value:.6f}" for value in embedding) + "]"
                            cur.execute(
                                """
                                SELECT ka.id, ka.title, ka.summary, ka.category, ka.source, ka.source_url, ka.verified_at, ka.tags
                                FROM knowledge_articles ka
                                JOIN knowledge_embeddings ke ON ke.article_id = ka.id
                                ORDER BY ke.embedding <=> %s::vector
                                """,
                                (embedding_value,),
                            )
                            rows = cur.fetchall()
                            columns = [desc[0] for desc in cur.description]
                            vector_articles = _rows_to_dicts(columns, rows)
                            if vector_articles:
                                cur.execute("SELECT * FROM knowledge_articles ORDER BY verified_at DESC")
                                all_rows = cur.fetchall()
                                all_columns = [desc[0] for desc in cur.description]
                                articles = _deduplicate_knowledge_articles(_rows_to_dicts(all_columns, all_rows))
                                ranked = sorted(
                                    articles,
                                    key=lambda article: score_knowledge_match(article, query_text),
                                    reverse=True,
                                )
                                return [article for article in ranked if score_knowledge_match(article, query_text) > 0][:limit]

                    cur.execute("SELECT * FROM knowledge_articles ORDER BY verified_at DESC")
                    rows = cur.fetchall()
                    columns = [desc[0] for desc in cur.description]
                    articles = _deduplicate_knowledge_articles(_rows_to_dicts(columns, rows))
                    if query_text:
                        scored = sorted(
                            articles,
                            key=lambda article: score_knowledge_match(article, query_text),
                            reverse=True,
                        )
                        return [article for article in scored if score_knowledge_match(article, query_text) > 0][:limit]
                    return articles[:limit]
        except Exception:
            pass

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        "SELECT * FROM knowledge_articles ORDER BY verified_at DESC"
    ).fetchall()

    conn.close()
    articles = _deduplicate_knowledge_articles([dict(row) for row in rows])

    if query and query.strip():
        scored = sorted(
            articles,
            key=lambda article: score_knowledge_match(article, query),
            reverse=True,
        )
        return [article for article in scored if score_knowledge_match(article, query) > 0][:limit]

    return sorted(
        articles,
        key=lambda article: _get_source_trust_score(article.get("source"), article.get("source_url")),
        reverse=True,
    )[:limit]


def infer_pillar(text: str, knowledge_matches: list[dict] | None = None) -> str:
    lowered = text.lower()
    scores = {pillar: 0 for pillar in APPROVED_REFERRALS}

    for pillar, keywords in PILLAR_KEYWORDS.items():
        for keyword in keywords:
            if keyword in lowered:
                scores[pillar] += 1

    if knowledge_matches:
        for article in knowledge_matches:
            category = article.get("category")
            if category in scores:
                scores[category] += 2

            tags = article.get("tags", "")
            for pillar, keywords in PILLAR_KEYWORDS.items():
                if any(keyword in tags.lower() for keyword in keywords):
                    scores[pillar] += 1

    best_pillar = max(scores.items(), key=lambda item: (item[1], item[0]))
    if best_pillar[1] > 0:
        return best_pillar[0]

    return "digital-rights"


def build_contextual_reply(text: str, pillar: str, knowledge_matches: list[dict] | None = None) -> str:
    lowered = text.lower()

    if pillar == "digital-rights":
        if any(keyword in lowered for keyword in ["phishing", "link", "hacked", "account", "password", "scam"]):
            intro = "It sounds like you’re dealing with an online safety or account abuse issue. The safest next step is to preserve evidence, secure your accounts, and avoid engaging with the sender until you’ve saved screenshots or reports."
        else:
            intro = "Thanks for telling me about that. I can help you take the safest next steps for an online safety concern."
    elif pillar == "protest-rights":
        intro = "It sounds like you may need help with a rights or legal issue. Keep a careful record of what happened, when it happened, and who was involved so you can get the right support quickly."
    elif pillar == "mental-health":
        intro = "I’m sorry you’re carrying this. If you feel in immediate danger or think you might hurt yourself, please contact emergency services or a trusted person right now."
    elif pillar == "gender-rights":
        intro = "I’m sorry this happened. For your safety, try to move to a secure place, keep a record of what occurred, and reach out to someone you trust for immediate support."
    else:
        intro = "Thanks for sharing that. I can help you find a safe, practical next step."

    base_reply = APPROVED_REFERRALS.get(pillar, APPROVED_REFERRALS["digital-rights"])["reply"]
    details = ""

    if knowledge_matches:
        first_match = knowledge_matches[0]
        trust_score = _get_source_trust_score(first_match.get("source"), first_match.get("source_url"))
        source_label = f"{first_match.get('source', 'Verified source')}"
        details = (
            f"\n\nVerified source: {first_match['title']} ({source_label}, trust score {trust_score}/100, verified {first_match['verified_at']})"
        )
        if first_match.get("source_url"):
            details += f" | URL: {first_match['source_url']}"
        details += "."

    return f"{intro} {base_reply}{details}"


def build_rag_context(knowledge_matches: list[dict] | None = None) -> str:
    if not knowledge_matches:
        return "No knowledge context available."

    rows = []
    for match in knowledge_matches[:3]:
        source_line = f"- {match.get('title', 'Untitled resource')} ({match.get('source', 'Unknown source')}, verified {match.get('verified_at', 'unknown date')})"
        if match.get("source_url"):
            source_line += f" | URL: {match['source_url']}"
        source_line += f": {match.get('summary', '')}"
        rows.append(source_line)

    return "\n".join(rows)


def generate_llm_reply(
    text: str,
    inferred_pillar: str,
    knowledge_matches: list[dict] | None = None,
) -> str | None:
    if not OPENAI_API_KEY:
        return None

    knowledge_context = build_rag_context(knowledge_matches)

    system_prompt = (
        "You are AMANI, a rights and wellbeing support assistant. "
        "Answer in a calm, supportive, plain-language way. Be referral-first, avoid harmful or illegal advice, "
        "and never pretend to be a lawyer, doctor, or emergency responder. "
        "If the user may be in immediate danger, encourage them to contact emergency services or a trusted person right now. "
        "Focus on practical, safe next steps and, when relevant, use the provided knowledge references."
    )

    user_prompt = (
        f"User message: {text}\n"
        f"Detected pillar: {inferred_pillar}\n"
        f"Knowledge context:\n{knowledge_context or 'No knowledge context available.'}\n"
        "Please provide a helpful, concise reply in the voice of AMANI. "
        "Use only the verified knowledge context above, cite the source title when relevant, and do not invent facts or URLs."
    )

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.5,
    }

    endpoint = f"{OPENAI_BASE_URL.rstrip('/')}/chat/completions"
    request = urllib_request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib_request.urlopen(request, timeout=LLM_TIMEOUT) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None

    try:
        content = response_data["choices"][0]["message"]["content"]
        if isinstance(content, list):
            return "".join(part.get("text", "") for part in content if isinstance(part, dict))
        return str(content).strip()
    except Exception:
        return None


def update_case_record(case_id: str, updates: CaseUpdateRequest) -> dict:
    payload = updates.model_dump(exclude_unset=True)
    if not payload:
        raise HTTPException(status_code=400, detail="No case update fields were provided.")

    set_clause: list[str] = []
    params: list[str | None] = []

    for field in ["status", "priority", "assignee", "notes"]:
        if field in payload:
            set_clause.append(f"{field} = ?")
            params.append(payload[field])

    if not set_clause:
        raise HTTPException(status_code=400, detail="No valid case update fields were provided.")

    set_clause.append("updated_at = CURRENT_TIMESTAMP")
    params.append(case_id)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    result = conn.execute(
        f"UPDATE moderator_cases SET {', '.join(set_clause)} WHERE id = ?",
        params,
    )

    if result.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Case {case_id} was not found.")

    conn.commit()
    row = conn.execute("SELECT * FROM moderator_cases WHERE id = ?", (case_id,)).fetchone()
    conn.close()

    if row is None:
        return {}

    return {key: row[key] for key in row.keys()}


initialize_database()
initialize_postgres_seed_data()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "orchestrator",
        "message": "AMANI orchestrator is running",
    }


@app.get("/cases")
def get_cases(
    status: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
    search: str | None = None,
):
    return fetch_cases(status=status, priority=priority, assignee=assignee, search=search)


@app.patch("/cases/{case_id}")
def update_case(case_id: str, request: CaseUpdateRequest):
    return update_case_record(case_id, request)


@app.get("/referrals")
def get_referrals():
    return fetch_referrals()


@app.get("/knowledge")
def get_knowledge(query: str | None = None, limit: int = 5):
    if limit < 1:
        raise HTTPException(status_code=400, detail="limit must be at least 1")
    return fetch_knowledge_articles(query=query, limit=limit)


@app.get("/knowledge-sources")
def get_knowledge_sources():
    return fetch_trusted_sources()


@app.get("/source-reviews")
def get_source_reviews(status: str | None = None):
    return fetch_review_queue(status=status)


@app.get("/source-reviews/{review_id}/history")
def get_review_history(review_id: str):
    return fetch_review_history(review_id=review_id)


@app.post("/source-reviews")
def create_review_endpoint(submission: dict):
    return create_source_review(submission)


@app.post("/source-reviews/{review_id}/approve")
def approve_review_endpoint(review_id: str, payload: dict | None = None):
    reviewer = None
    notes = None
    if payload:
        reviewer = payload.get("reviewer")
        notes = payload.get("notes")
    return approve_source_review(review_id, reviewer=reviewer, notes=notes)


@app.post("/source-reviews/{review_id}/reject")
def reject_review_endpoint(review_id: str, payload: dict | None = None):
    reviewer = None
    notes = None
    if payload:
        reviewer = payload.get("reviewer")
        notes = payload.get("notes")
    return reject_source_review(review_id, reviewer=reviewer, notes=notes)


@app.post("/source-reviews/{review_id}/publish")
def publish_review_endpoint(review_id: str, payload: dict | None = None):
    # Moderator-driven publication keeps content approval and live bot retrieval in sync.
    return publish_approved_review(review_id)


@app.post("/approved-sources")
def ingest_approved_sources_endpoint(sources: list[dict] | dict):
    if isinstance(sources, dict):
        sources = [sources]
    return ingest_approved_sources(sources)


@app.post("/approved-sources/directory")
def ingest_approved_sources_directory_endpoint(payload: dict):
    directory = payload.get("directory")
    if not directory:
        raise HTTPException(status_code=400, detail="directory is required")
    return ingest_approved_sources_from_directory(
        directory,
        source_name=payload.get("source_name") or "Approved source",
        category=payload.get("category") or "general",
        source_url_prefix=payload.get("source_url_prefix"),
        tags=payload.get("tags"),
    )


@app.post("/knowledge")
def ingest_knowledge_article(article: dict):
    return upsert_knowledge_article(article)


@app.post("/knowledge/batch")
def ingest_knowledge_articles(articles: list[dict]):
    return batch_ingest_knowledge_articles(articles)


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    text = request.message.lower()

    if any(keyword in text for keyword in URGENT_KEYWORDS):
        case_id = create_case_record(request.message, request.channel)
        response = ChatResponse(
            reply="This sounds urgent. Please contact emergency services or a trusted person right now, and if you want, I can help you find the best local support channel immediately.",
            pillar="emergency",
            triage="priority-handoff",
            escalationNeeded=True,
            suggestions=["Emergency services", "Nearest clinic", f"Moderator handoff: {case_id}"],
        )
        save_chat_record(
            request.sessionId,
            request.channel,
            request.message,
            response.reply,
            response.pillar,
            response.triage,
            response.escalationNeeded,
        )
        return response

    knowledge_matches = fetch_knowledge_articles(text, limit=5)
    inferred_pillar = infer_pillar(text, knowledge_matches)

    response_payload = APPROVED_REFERRALS.get(inferred_pillar, APPROVED_REFERRALS["digital-rights"])
    suggestions = list(response_payload["suggestions"])

    reply = generate_llm_reply(text, inferred_pillar, knowledge_matches)
    if not reply:
        reply = build_contextual_reply(text, inferred_pillar, knowledge_matches)

    if knowledge_matches:
        first_match = knowledge_matches[0]
        suggestions.append(f"View {first_match['title']}")

    response = ChatResponse(
        reply=reply,
        pillar=inferred_pillar,
        triage="routine",
        escalationNeeded=False,
        suggestions=suggestions,
    )

    save_chat_record(
        request.sessionId,
        request.channel,
        request.message,
        response.reply,
        response.pillar,
        response.triage,
        response.escalationNeeded,
    )

    return response
