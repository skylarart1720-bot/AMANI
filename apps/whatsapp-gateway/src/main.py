"""Signed Meta webhook with a durable encrypted inbox and retrying delivery."""
import asyncio
import hashlib
import hmac
import json
import os
import sqlite3
import time
from contextlib import asynccontextmanager, contextmanager, suppress
from pathlib import Path

import httpx
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

ROOT = Path(os.getenv("PROJECT_ROOT", str(Path(__file__).resolve().parents[3]) if len(Path(__file__).resolve().parents) > 3 else "/app"))
load_dotenv(ROOT / ".env")
DATA = Path(os.getenv("AMANI_DATA_DIR", str(ROOT / "data")))
DATA.mkdir(parents=True, exist_ok=True)

def resolve_orchestrator_url(value):
    return value.strip() if value and value.strip() else "http://127.0.0.1:8005"

ORCHESTRATOR_URL = resolve_orchestrator_url(os.getenv("ORCHESTRATOR_URL"))
META_WHATSAPP_TOKEN = os.getenv("META_WHATSAPP_TOKEN", "")
META_WHATSAPP_PHONE_NUMBER_ID = os.getenv("META_WHATSAPP_PHONE_NUMBER_ID", "")
META_WEBHOOK_VERIFY_TOKEN = os.getenv("META_WEBHOOK_VERIFY_TOKEN", "")
META_APP_SECRET = os.getenv("META_APP_SECRET", "")
META_WHATSAPP_API_VERSION = os.getenv("META_WHATSAPP_API_VERSION", "")

def configured():
    return os.getenv("WHATSAPP_PROVIDER") == "meta" and all(value and not value.startswith("your_") for value in (META_WHATSAPP_TOKEN, META_WHATSAPP_PHONE_NUMBER_ID, META_WEBHOOK_VERIFY_TOKEN, META_APP_SECRET, META_WHATSAPP_API_VERSION))

def cipher():
    key = os.getenv("CHAT_ENCRYPTION_KEY")
    if not key:
        path = DATA / ".chat-key"
        if not path.exists():
            raise RuntimeError("Start the orchestrator first or configure CHAT_ENCRYPTION_KEY")
        key = path.read_text().strip()
    return Fernet(key.encode())

@contextmanager
def connect():
    db = sqlite3.connect(DATA / "whatsapp.db", timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA secure_delete=ON")
    try:
        with db:
            yield db
    finally:
        db.close()

with connect() as db:
    db.executescript("""
    CREATE TABLE IF NOT EXISTS inbox (id TEXT PRIMARY KEY, payload TEXT, status TEXT DEFAULT 'queued', attempts INTEGER DEFAULT 0, available REAL, created REAL);
    CREATE TABLE IF NOT EXISTS senders (id TEXT PRIMARY KEY, token TEXT, consent INTEGER DEFAULT 0, created REAL);
    """)
    db.execute("BEGIN IMMEDIATE")
    if "language" not in {row["name"] for row in db.execute("PRAGMA table_info(senders)")}:
        db.execute("ALTER TABLE senders ADD COLUMN language TEXT NOT NULL DEFAULT 'en'")

async def deliver(number, message):
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(f"https://graph.facebook.com/{META_WHATSAPP_API_VERSION}/{META_WHATSAPP_PHONE_NUMBER_ID}/messages",
            headers={"Authorization": "Bearer " + META_WHATSAPP_TOKEN}, json={"messaging_product": "whatsapp", "to": number, "type": "text", "text": {"body": message[:4096]}})
        response.raise_for_status()

async def process(row):
    encryption = cipher()
    payload = json.loads(encryption.decrypt(row["payload"].encode()))
    number, message = payload["from"], payload["text"]["body"]
    if payload.get("answer"):
        await deliver(number, payload["answer"])
        return
    sender = hmac.new(META_APP_SECRET.encode(), number.encode(), hashlib.sha256).hexdigest()
    async with httpx.AsyncClient(timeout=40, trust_env=False) as client:
        with connect() as db:
            record = db.execute("SELECT * FROM senders WHERE id=?", (sender,)).fetchone()
        is_new = record is None
        if is_new:
            response = await client.post(ORCHESTRATOR_URL + "/support/sessions")
            response.raise_for_status()
            token = response.json()["token"]
            with connect() as db:
                db.execute("INSERT INTO senders(id,token,consent,created,language) VALUES(?,?,?,?,?)", (sender, encryption.encrypt(token.encode()).decode(), 0, time.time(), "en"))
        else:
            token = encryption.decrypt(record["token"].encode()).decode()
        headers = {"Authorization": "Bearer " + token}
        command = message.strip().lower()
        language = record["language"] if record else "en"
        if command in ("languages", "language", "lang") or command.startswith(("language ", "lang ")):
            response = await client.get(ORCHESTRATOR_URL + "/support/languages")
            response.raise_for_status()
            options = response.json()["languages"]
            code = command.split(maxsplit=1)[1] if " " in command else None
            selected = next((item for item in options if item["code"].lower() == code), None)
            if selected:
                language = selected["code"]
                with connect() as db:
                    db.execute("UPDATE senders SET language=? WHERE id=?", (language, sender))
                answer = "Language: " + selected["native"] + ". New replies will use this language."
            else:
                answer = "Send language followed by a code, for example language ak or language fr.\n" + "\n".join(item["code"] + " — " + item["native"] for item in options)
        elif command in ("forget", "delete my chat", "delete", "forget this conversation"):
            response = await client.delete(ORCHESTRATOR_URL + "/support/sessions", headers=headers)
            if response.status_code not in (200, 401):
                response.raise_for_status()
            with connect() as db:
                db.execute("DELETE FROM senders WHERE id=?", (sender,))
            answer = "Your conversation has been deleted from AMANI. This does not delete messages from WhatsApp or Meta."
        elif command == "enable ai":
            with connect() as db:
                db.execute("UPDATE senders SET consent=1 WHERE id=?", (sender,))
            answer = "AI replies enabled. Recent messages may be sent to the AI provider. Send 'disable ai' to stop, or 'forget' to delete your Amani conversation."
        elif command == "disable ai":
            with connect() as db:
                db.execute("UPDATE senders SET consent=0 WHERE id=?", (sender,))
            answer = "AI replies disabled. Directory support remains available."
        elif command in ("human", "talk to a human"):
            response = await client.post(ORCHESTRATOR_URL + "/support/handoff", headers=headers)
            response.raise_for_status()
            answer = response.json()["message"] + " Send 'updates' to check for replies."
        elif command == "updates":
            response = await client.get(ORCHESTRATOR_URL + "/support/messages", headers=headers)
            response.raise_for_status()
            replies = [m["content"] for m in response.json()["messages"] if m["role"] == "human"]
            answer = "\n\n".join(replies[-3:]) if replies else "No human reply is available yet. For immediate danger in Ghana call 112."
        else:
            response = await client.post(ORCHESTRATOR_URL + "/support/chat", headers=headers, json={"message": message[:4000], "ai_consent": bool(record and record["consent"]), "language": language})
            if response.status_code == 401:
                with connect() as db:
                    db.execute("DELETE FROM senders WHERE id=?", (sender,))
                answer = "Your session has expired. Please send your message again to start a new conversation."
            else:
                response.raise_for_status()
                result = response.json()
                answer = result["reply"] + "\n\n" + "\n".join(r["organisation"] + ": " + r["website"] for r in result.get("referrals", []))
        if is_new:
            answer = ("Welcome to AMANI. I am an AI-enabled information assistant, not an emergency service. "
                      "Meta can see your number; Amani stores an encrypted delivery record briefly. Conversations expire after 7 days. "
                      "Send 'forget' to delete, 'human' to request a moderator, or 'enable ai' to consent to sharing recent messages with the AI provider. "
                      "Send 'languages' to choose the language for new replies.\n\n" + answer)
        payload["answer"] = answer
        with connect() as db:
            db.execute("UPDATE inbox SET payload=? WHERE id=?", (encryption.encrypt(json.dumps(payload).encode()).decode(), row["id"]))
        await deliver(number, answer)

async def worker():
    while True:
        try:
            with connect() as db:
                db.execute("DELETE FROM inbox WHERE created < ?", (time.time() - 86400 * 7,))
                db.execute("DELETE FROM senders WHERE created < ?", (time.time() - 86400 * 7,))
                row = db.execute("SELECT * FROM inbox WHERE status='queued' AND available<=? ORDER BY created LIMIT 1", (time.time(),)).fetchone()
            if row and configured():
                try:
                    await process(row)
                    with connect() as db:
                        db.execute("UPDATE inbox SET status='sent',payload='' WHERE id=?", (row["id"],))
                except (httpx.HTTPError, ValueError, KeyError, RuntimeError):
                    with connect() as db:
                        db.execute("UPDATE inbox SET attempts=attempts+1,status=?,available=? WHERE id=?",
                            ("failed" if row["attempts"] >= 4 else "queued", time.time() + 30 * (2 ** row["attempts"]), row["id"]))
        except sqlite3.Error:
            pass
        await asyncio.sleep(2)

@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(worker())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task

app = FastAPI(title="AMANI WhatsApp Gateway", lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "ok", "configured": configured()}

@app.get("/webhook")
def verify_webhook(request: Request):
    query = request.query_params
    if META_WEBHOOK_VERIFY_TOKEN and query.get("hub.mode") == "subscribe" and hmac.compare_digest(query.get("hub.verify_token", ""), META_WEBHOOK_VERIFY_TOKEN):
        return PlainTextResponse(query.get("hub.challenge", ""))
    raise HTTPException(403, "Invalid verification token")

@app.post("/webhook")
async def webhook(request: Request):
    if not configured():
        raise HTTPException(503, "WhatsApp is not configured")
    raw = await request.body()
    if len(raw) > 65536:
        raise HTTPException(413, "Payload too large")
    expected = "sha256=" + hmac.new(META_APP_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(request.headers.get("x-hub-signature-256", ""), expected):
        raise HTTPException(401, "Invalid webhook signature")
    try:
        body = json.loads(raw)
        if body.get("object") != "whatsapp_business_account":
            raise ValueError()
        encryption = cipher()
        with connect() as db:
            for entry in body.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    if value.get("metadata", {}).get("phone_number_id") != META_WHATSAPP_PHONE_NUMBER_ID:
                        continue
                    for message in value.get("messages", []):
                        if message.get("type") == "text" and isinstance(message.get("text", {}).get("body"), str) and message.get("id") and message.get("from"):
                            stored = {"from": message["from"], "text": {"body": message["text"]["body"][:4000]}}
                            db.execute("INSERT OR IGNORE INTO inbox(id,payload,available,created) VALUES(?,?,?,?)", (hashlib.sha256(message["id"].encode()).hexdigest(), encryption.encrypt(json.dumps(stored).encode()).decode(), time.time(), time.time()))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(400, "Invalid webhook payload")
    return {"received": True}
