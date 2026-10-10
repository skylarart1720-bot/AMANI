"""Availability and chosen-staff routing must reflect real, revocable access."""
import sys
import time
from unittest.mock import AsyncMock, patch
import httpx
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import main
import support

client = TestClient(main.app)
admin = {"Authorization": "Bearer " + support.ADMIN_TOKEN}


def staff(actor):
    assert client.post("/admin/staff", headers=admin, json={"staff_id": actor, "password": "presence-test-password"}).status_code == 200
    response = client.post("/auth/login", json={"mode": "staff", "staff_id": actor, "password": "presence-test-password"})
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["token"]}


def visitor():
    return {"Authorization": "Bearer " + client.post("/support/sessions").json()["token"]}


def online_ids():
    return {person["id"] for person in client.get("/support/staff").json()["staff"]}


def test_presence_requires_a_live_authenticated_heartbeat():
    headers = staff("presence-one")
    assert "presence-one" not in online_ids()
    assert client.post("/admin/presence", json={"available": True}).status_code == 401
    assert client.post("/admin/presence", headers=headers, json={"available": True}).status_code == 200
    assert "presence-one" in online_ids()
    client.post("/admin/presence", headers=headers, json={"available": False})
    assert "presence-one" not in online_ids()
    client.post("/admin/presence", headers=headers, json={"available": True})
    with support.connect() as conn:
        conn.execute("UPDATE staff_presence SET seen=? WHERE actor=?", (time.time() - 46, "presence-one"))
    assert "presence-one" not in online_ids()
    client.post("/admin/presence", headers=headers, json={"available": True})
    client.post("/admin/logout", headers=headers)
    assert "presence-one" not in online_ids()


def test_super_admin_is_selectable_only_when_online():
    client.post("/admin/presence", headers=admin, json={"available": True})
    assert "super-admin" in online_ids()
    headers = visitor()
    result = client.post("/support/handoff", headers=headers, json={"staff_id": "super-admin"})
    assert result.status_code == 200 and result.json()["assignee"] == "super-admin"
    client.post("/admin/presence", headers=admin, json={"available": False})
    assert "super-admin" not in online_ids()
    assert client.post("/support/handoff", headers=visitor(), json={"staff_id": "super-admin"}).status_code == 409


def test_chosen_staff_case_is_private_and_messages_route_to_humans():
    selected, other = staff("chosen-one"), staff("chosen-other")
    client.post("/admin/presence", headers=selected, json={"available": True})
    headers = visitor()
    case = client.post("/support/handoff", headers=headers, json={"staff_id": "chosen-one"}).json()
    cid = case["id"]
    assert case["assignee"] == "chosen-one"
    assert cid in {row["id"] for row in client.get("/admin/queue", headers=selected).json()}
    assert cid not in {row["id"] for row in client.get("/admin/queue", headers=other).json()}
    assert cid in {row["id"] for row in client.get("/admin/queue", headers=admin).json()}
    assert client.post(f"/admin/queue/{cid}/reply", headers=other, json={"message": "Wrong person"}).status_code == 403
    assert client.patch(f"/admin/queue/{cid}", headers=other, json={"status": "resolved"}).status_code == 403
    reply = client.post("/support/chat", headers=headers, json={"message": "I would like to speak with you."})
    assert reply.json()["mode"] == "human"
    assert client.post(f"/admin/queue/{cid}/reply", headers=selected, json={"message": "I am here to help."}).status_code == 200
    messages = client.get("/support/messages", headers=headers).json()
    assert messages["case"]["assignee"] == "chosen-one"
    assert messages["messages"][-1]["role"] == "human"
    assert client.post("/support/handoff", headers=headers, json={"staff_id": None}).json()["assignee"] is None


def test_disabling_or_resetting_staff_removes_their_availability():
    headers = staff("presence-disabled")
    client.post("/admin/presence", headers=headers, json={"available": True})
    client.patch("/admin/staff/presence-disabled", headers=admin, json={"active": False})
    assert "presence-disabled" not in online_ids()
    assert client.post("/support/handoff", headers=visitor(), json={"staff_id": "presence-disabled"}).status_code == 409


def test_setup_checklist_is_super_admin_only_and_shows_unfinished_work():
    headers = staff("setup-staff")
    assert client.get("/admin/setup", headers=headers).status_code == 403
    response = client.get("/admin/setup", headers=admin)
    assert response.status_code == 200
    items = {item["name"]: item for item in response.json()["items"]}
    assert items["WhatsApp"]["status"] == "Setup required"
    assert items["MFA and organisation isolation"]["status"] == "Not implemented"
    assert 'hosted schedule pending' in items["Backups and restoration"]["status"]
    assert support.ADMIN_TOKEN not in response.text and "password_hash" not in response.text

def test_whatsapp_chat_link_does_not_require_automation(monkeypatch):
    monkeypatch.setenv("WHATSAPP_SUPPORT_NUMBER", "+233200000000")
    monkeypatch.setenv("WHATSAPP_GATEWAY_URL", "")
    with patch.object(support.httpx.AsyncClient, "get", new=AsyncMock(side_effect=httpx.ConnectError("offline"))):
        result = client.get("/support/status").json()
    assert result["whatsapp_url"] == "https://wa.me/233200000000"
    assert result["whatsapp_configured"] is False
    monkeypatch.setenv("WHATSAPP_SUPPORT_NUMBER", "invalid-number")
    with patch.object(support.httpx.AsyncClient, "get", new=AsyncMock(side_effect=httpx.ConnectError("offline"))):
        assert client.get("/support/status").json()["whatsapp_url"] is None
