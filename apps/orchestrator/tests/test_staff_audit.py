"""Staff actions must be attributable, and the audit trail itself must not be editable."""
import json
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import main
import support

client = TestClient(main.app)
admin = {"Authorization": "Bearer " + support.ADMIN_TOKEN}
ADA = {"Authorization": "Bearer " + "a" * 40}
KOFI = {"Authorization": "Bearer " + "b" * 40}

def entries(headers=None, **filters):
    params = {"limit": 500}
    params.update(filters)
    response = client.get("/admin/audit", headers=headers or admin, params=params)
    assert response.status_code == 200
    return response.json()["entries"]

def session():
    return {"Authorization": "Bearer " + client.post("/support/sessions").json()["token"]}

def test_named_staff_tokens_attribute_each_action(monkeypatch):
    monkeypatch.setattr(support, "STAFF_ACCOUNTS", {"ada": "a" * 40, "kofi": "b" * 40})
    payload = {"title": "Attribution source", "summary": "Reviewed text long enough for the knowledge model.", "category": "climate", "source": "Source", "source_url": "https://example.org/a", "verified_at": "2026-09-26"}
    ada_entry = client.post("/admin/knowledge", headers=ADA, json=payload).json()
    kofi_entry = client.post("/admin/knowledge", headers=KOFI, json=payload).json()
    client.patch(f"/admin/knowledge/{ada_entry['id']}", headers=ADA, json={"status": "published"})
    client.patch(f"/admin/knowledge/{kofi_entry['id']}", headers=KOFI, json={"status": "rejected"})
    assert any(e["actor"] == "ada" and e["resource"] == ada_entry["id"] and e["action"] == "knowledge.published" for e in entries(headers=ADA))
    assert any(e["actor"] == "kofi" and e["resource"] == kofi_entry["id"] and e["action"] == "knowledge.rejected" for e in entries(headers=KOFI))
    assert not any(e["actor"] == "kofi" and e["action"] == "knowledge.published" for e in entries(headers=KOFI))

def test_shared_token_is_recorded_as_shared_not_as_a_person():
    client.get("/admin/queue", headers=admin)
    actors = {e["actor"] for e in entries(action="queue.viewed")}
    assert support.SHARED_ACTOR in actors
    assert "anonymous" not in actors

def test_revoked_named_token_loses_access(monkeypatch):
    monkeypatch.setattr(support, "STAFF_ACCOUNTS", {"ada": "a" * 40})
    assert client.get("/admin/queue", headers=ADA).status_code == 200
    monkeypatch.setattr(support, "STAFF_ACCOUNTS", {})
    assert client.get("/admin/queue", headers=ADA).status_code == 401

def test_denied_and_failed_access_are_recorded():
    before = len(entries())
    assert client.get("/admin/queue", headers={"Authorization": "Bearer not-the-token"}).status_code == 401
    assert client.get("/admin/queue").status_code == 401
    assert client.patch("/admin/queue/A-NOTHERE", headers=admin, json={"status": "resolved"}).status_code == 404
    assert client.patch("/admin/knowledge/deadbeef", headers=admin, json={"status": "published"}).status_code == 404
    client.post("/admin/queue/A-NOTHERE/reply", headers=admin, json={"message": "hello"})
    recorded = entries()[0:4]
    assert any(e["action"] == "auth.denied" and e["outcome"] == "denied" for e in recorded)
    assert any(e["action"] == "case.status_updated" and e["outcome"] == "not_found" for e in recorded)
    assert any(e["action"] == "knowledge.reviewed" and e["outcome"] == "not_found" for e in recorded)
    assert any(e["action"] == "case.replied" and e["outcome"] == "not_found" for e in recorded)
    assert len(entries()) > before

def test_transcript_reads_and_replies_are_audited_without_content():
    headers = session()
    client.post("/support/chat", headers=headers, json={"message": "I need information about protest rights"})
    cid = client.post("/support/handoff", headers=headers).json()["id"]
    client.get("/admin/queue", headers=admin)
    client.post(f"/admin/queue/{cid}/reply", headers=admin, json={"message": "SENTINEL-PRIVATE-TEXT"})
    client.patch(f"/admin/queue/{cid}", headers=admin, json={"status": "in_progress"})
    recorded = entries()
    assert any(e["action"] == "queue.viewed" for e in recorded)
    assert any(e["action"] == "case.replied" and e["resource"] == cid for e in recorded)
    assert any(e["action"] == "case.status_updated" and e["resource"] == cid and e["detail"] == "in_progress" for e in recorded)
    serialised = json.dumps(recorded)
    assert "SENTINEL-PRIVATE-TEXT" not in serialised
    assert "I need information about protest rights" not in serialised
    assert support.ADMIN_TOKEN not in serialised
    client.delete("/support/sessions", headers=headers)

def test_audit_records_carry_time_and_outcome_and_are_filterable():
    client.get("/admin/directory", headers=admin)
    client.get("/admin/knowledge", headers=admin)
    assert all(e["outcome"] == "success" for e in entries(action="directory.viewed"))
    assert all(e["created"] > 0 for e in entries(action="directory.viewed"))
    assert entries(actor="nobody-with-this-name") == []
    assert all(e["action"] == "knowledge.viewed" for e in entries(actor=support.SHARED_ACTOR, action="knowledge.viewed"))

def test_staff_cannot_edit_or_delete_audit_entries():
    for method in ("post", "put", "patch", "delete"):
        call = getattr(client, method)
        kwargs = {"json": {}} if method in ("post", "put", "patch") else {}
        assert call("/admin/audit", headers=admin, **kwargs).status_code in (404, 405)

def test_audit_reads_are_recorded_without_flooding_the_default_listing():
    before = len(entries())
    client.get("/admin/audit", headers=admin)
    assert len(entries()) == before
    self_reads = entries(action="audit.viewed")
    assert self_reads and all(e["resource"] == "audit" for e in self_reads)

def test_audit_retention_window_is_enforced():
    client.get("/admin/knowledge", headers=admin)
    with support.connect() as conn:
        conn.execute("INSERT INTO audit(action,actor,resource,outcome,detail,created) VALUES('ancient.probe','tester','r','success',NULL,?)", (time.time() - support.AUDIT_RETENTION - 60,))
        assert conn.execute("SELECT 1 FROM audit WHERE action='ancient.probe'").fetchone()
    support.purge_expired_once()
    with support.connect() as conn:
        assert not conn.execute("SELECT 1 FROM audit WHERE action='ancient.probe'").fetchone()
        assert conn.execute("SELECT 1 FROM audit WHERE action='knowledge.viewed'").fetchone()

def test_denied_floods_are_rate_limited_before_they_reach_the_audit_table():
    headers = {"Authorization": "Bearer not-the-token"}
    with support.connect() as conn:
        before = conn.execute("SELECT count(*) FROM audit WHERE action='auth.denied'").fetchone()[0]
    statuses = [client.get("/admin/queue", headers=headers).status_code for _ in range(122)]
    assert statuses[:120] == [401] * 120
    assert statuses[120:] == [429, 429]
    with support.connect() as conn:
        written = conn.execute("SELECT count(*) FROM audit WHERE action='auth.denied'").fetchone()[0] - before
    assert written == 120

def test_oversized_bodies_are_rejected_from_their_declared_length():
    payload = {"title": "x", "message": "y" * 40000}
    response = client.post("/support/chat", headers={**session(), "content-length": str(len(json.dumps(payload)))}, content=json.dumps(payload))
    assert response.status_code == 413
    response = client.post("/admin/knowledge", headers=admin, json={"title": "x", "summary": "y" * 30000, "category": "climate", "source": "s", "source_url": "https://example.org/a", "verified_at": "2026-09-26"})
    assert response.status_code == 413

def test_undersized_or_missing_content_length_is_still_capped():
    response = client.post("/support/chat", headers=session(), content=iter([b"x" * 100, b"y" * 25000]))
    assert response.status_code == 413
    response = client.request("GET", "/admin/queue", headers=admin, content=iter([b"z" * 30000]))
    assert response.status_code == 413
    response = client.post("/support/sessions", content=iter([b"z" * 30000]))
    assert response.status_code == 413

def test_normal_bodies_still_reach_handlers():
    headers = session()
    result = client.post("/support/chat", headers=headers, json={"message": "I need information about staying safe online"})
    assert result.status_code == 200
    assert result.json()["mode"] == "directory"
    assert client.delete("/support/sessions", headers=headers).status_code == 200

def test_check_link_only_forwards_a_validated_url():
    assert client.post("/support/check-link", json={"consent": True}).status_code == 422
    assert client.post("/support/check-link", json={"url": "x" * 5000, "consent": True}).status_code == 422
    assert client.post("/support/check-link", json={"url": "https://example.org", "consent": True}).status_code == 503