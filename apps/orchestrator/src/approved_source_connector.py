from __future__ import annotations

import re
from html import unescape
from pathlib import Path
from urllib import request as urllib_request

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - optional dependency for PDF processing
    PdfReader = None


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", unescape(value)).strip()


def _extract_html_text(value: str | None) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"<script.*?</script>", " ", value, flags=re.I | re.S)
    cleaned = re.sub(r"<style.*?</style>", " ", cleaned, flags=re.I | re.S)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    return _clean_text(cleaned)


def _fetch_url_metadata(source_url: str | None) -> dict:
    if not source_url:
        return {}

    try:
        request = urllib_request.Request(
            source_url,
            headers={"User-Agent": "AmaniLineApprovedSource/1.0"},
        )
        with urllib_request.urlopen(request, timeout=10) as response:
            payload = response.read().decode("utf-8", errors="ignore")
    except Exception:
        return {}

    title_match = re.search(r"<title[^>]*>(.*?)</title>", payload, flags=re.I | re.S)
    title = _clean_text(title_match.group(1)) if title_match else ""

    description_match = re.search(
        r"<meta[^>]+(?:name|property)=['\"](?:description|og:description)['\"][^>]*content=['\"]([^'\"]+)['\"]",
        payload,
        flags=re.I | re.S,
    )
    description = _clean_text(description_match.group(1)) if description_match else ""

    if not description:
        paragraph_match = re.search(r"<p[^>]*>(.*?)</p>", payload, flags=re.I | re.S)
        if paragraph_match:
            description = _extract_html_text(paragraph_match.group(1))

    return {"title": title, "summary": description}


def _extract_pdf_text(pdf_path: str | Path) -> str:
    file_path = Path(pdf_path)
    if not file_path.exists():
        raise FileNotFoundError(file_path)
    if PdfReader is None:
        raise ImportError("pypdf is required to extract PDF content.")

    reader = PdfReader(str(file_path))
    chunks: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            chunks.append(page_text.strip())
    return "\n\n".join(chunks).strip()


def build_source_record(
    file_path: str | Path | None = None,
    *,
    url: str | None = None,
    source_name: str = "Approved source",
    category: str = "general",
    source_url: str | None = None,
    tags: str | None = None,
    title: str | None = None,
    summary: str | None = None,
    verified_at: str | None = None,
) -> dict:
    effective_url = (source_url or url or "").strip()
    path = Path(file_path) if file_path else None

    if path and path.exists():
        extracted_text = ""
        try:
            extracted_text = _extract_pdf_text(path)
        except Exception:
            try:
                extracted_text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                extracted_text = ""

        if not title:
            title = path.stem.replace("_", " ").strip() or "Approved source"
        if not summary and extracted_text:
            summary = _clean_text(extracted_text)[:500]
    elif effective_url:
        metadata = _fetch_url_metadata(effective_url)
        if not title:
            title = metadata.get("title") or "Approved source"
        if not summary:
            summary = metadata.get("summary") or ""

    if not title:
        title = "Approved source"
    if not summary:
        summary = "Approved source for moderator review and publication."

    record = {
        "id": None,
        "title": title,
        "summary": summary,
        "category": category or "general",
        "source": source_name or "Approved external source",
        "source_url": effective_url,
        "verified_at": verified_at or "pending-review",
        "tags": tags or "approved-source, review-needed",
    }
    return record


def collect_approved_sources_from_directory(
    directory: str | Path,
    *,
    source_name: str = "Approved source",
    category: str = "general",
    source_url_prefix: str | None = None,
    tags: str | None = None,
) -> list[dict]:
    root = Path(directory)
    if not root.exists():
        return []

    collected: list[dict] = []
    for path in sorted(root.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".pdf", ".txt", ".md", ".html"}:
            continue

        source_url = ""
        if source_url_prefix:
            source_url = f"{source_url_prefix.rstrip('/')}/{path.name}"

        collected.append(
            build_source_record(
                file_path=path,
                source_name=source_name,
                category=category,
                source_url=source_url,
                tags=tags,
            )
        )

    return collected
