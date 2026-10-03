import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import main
import support

client = TestClient(main.app)
admin = {"Authorization": "Bearer " + support.ADMIN_TOKEN}

def session():
    token = client.post("/support/sessions").json()["token"]
    return {"Authorization": "Bearer " + token}

def test_no_unprotected_moderation_or_ingestion():
    for path in ("/admin/queue", "/cases", "/source-reviews"):
        assert client.get(path).status_code == 401
    assert client.post("/knowledge", json={}).status_code == 401
    assert client.get("/admin/queue", headers=admin).status_code == 200

def test_session_isolation_encryption_and_cascading_deletion():
    owner, stranger = session(), session()
    text = "I feel anxious and need support"
    result = client.post("/support/chat", headers=owner, json={"message": text})
    assert result.status_code == 200
    assert result.json()["mode"] == "directory"
    assert client.get("/support/messages", headers=stranger).json()["messages"] == []
    with support.connect() as conn:
        assert all(text not in row["content"] for row in conn.execute("SELECT content FROM messages"))
    cid = client.post("/support/handoff", headers=owner).json()["id"]
    assert client.post(f"/admin/queue/{cid}/reply", headers=admin, json={"message": "A human reply"}).status_code == 200
    assert client.get("/support/messages", headers=owner).json()["messages"][-1]["role"] == "human"
    before = len(client.get('/support/messages', headers=owner).json()['messages'])
    followup = client.post('/support/chat', headers=owner, json={'message': 'Thank you, I have a follow-up.'})
    assert followup.json()['mode'] == 'human'
    assert len(client.get('/support/messages', headers=owner).json()['messages']) == before + 1
    assert client.delete("/support/sessions", headers=owner).status_code == 200
    assert client.get("/support/messages", headers=owner).status_code == 401
    assert not any(c["id"] == cid for c in client.get("/admin/queue", headers=admin).json())

def test_urgent_bypasses_ai_and_deduplicates_case():
    headers = session()
    with patch.object(support, "ai_reply", new_callable=AsyncMock) as model:
        for _ in range(2):
            response = client.post("/support/chat", headers=headers, json={"message": "I want to kill myself", "ai_consent": True})
            assert response.json()["triage"] == "urgent"
            assert "112" in response.json()["reply"]
            assert response.json()["case_id"]
        model.assert_not_called()
    client.delete("/support/sessions", headers=headers)

def test_ai_requires_consent_and_falls_back():
    headers = session()
    with patch.object(support, "ai_reply", new_callable=AsyncMock, return_value=None) as model:
        client.post("/support/chat", headers=headers, json={"message": "online safety"})
        model.assert_not_called()
        result = client.post("/support/chat", headers=headers, json={"message": "online safety", "ai_consent": True})
        assert result.json()["mode"] == "directory"
        assert "unavailable" in result.json()["reply"]
    client.delete("/support/sessions", headers=headers)

def test_knowledge_requires_publication_and_can_be_withdrawn():
    payload = {"title": "Verified support source", "summary": "A reviewed directory description for test coverage.", "category": "digital-rights", "source": "CSA", "source_url": "https://csa.gov.gh/report", "verified_at": "2026-09-26"}
    kid = client.post("/admin/knowledge", headers=admin, json=payload).json()["id"]
    assert not any(x["title"] == payload["title"] for x in support.reviewed_knowledge("digital-rights"))
    assert client.patch(f"/admin/knowledge/{kid}", headers=admin, json={"status": "published"}).status_code == 200
    assert any(x["title"] == payload["title"] for x in support.reviewed_knowledge("digital-rights"))
    client.patch(f"/admin/knowledge/{kid}", headers=admin, json={"status": "rejected"})
    assert not any(x["title"] == payload["title"] for x in support.reviewed_knowledge("digital-rights"))

def test_validation_and_expiry():
    headers = session()
    assert client.post("/support/chat", headers=headers, json={"message": " "}).status_code == 422
    assert client.post("/support/chat", headers=headers, json={"message": "x" * 4001}).status_code == 422
    with support.connect() as conn:
        conn.execute("UPDATE sessions SET created=0")
    assert client.get("/support/messages", headers=headers).status_code == 401

def test_french_support_and_urgent_routing():
    headers = session()
    result = client.post('/support/chat', headers=headers, json={'message': "J'ai besoin de soutien pour mon anxiété", 'language': 'fr'})
    assert result.status_code == 200
    assert 'Je peux vous aider' in result.json()['reply']
    assert result.json()['referrals'][0]['category'] == 'mental-health'
    result = client.post('/support/chat', headers=headers, json={'message': 'Je veux mourir', 'language': 'fr'})
    assert result.json()['triage'] == 'urgent'
    assert '112' in result.json()['reply']
    assert 'danger immédiat' in result.json()['reply']
    client.delete('/support/sessions', headers=headers)
