"""Password accounts must not grant administrator privileges or survive revocation."""
import hashlib
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
PASSWORD = "staff-test-password-very-long"


def create(actor):
    response = client.post("/admin/staff", headers=admin, json={"staff_id": actor, "password": PASSWORD})
    assert response.status_code == 200
    assert "password" not in response.text
    return response.json()["id"]


def login(actor, password=PASSWORD):
    return client.post("/auth/login", json={"mode": "staff", "staff_id": actor, "password": password})


def test_super_admin_token_and_staff_password_are_separate():
    actor = create("AM-role-test")
    response = login("AM-role-test")
    assert response.status_code == 200
    identity = response.json()
    assert identity["actor"] == actor and identity["role"] == "staff"
    headers = {"Authorization": "Bearer " + identity["token"]}
    assert client.get("/admin/me", headers=headers).json() == {"actor": actor, "role": "staff"}
    assert client.get("/admin/queue", headers=headers).status_code == 200
    assert client.get("/admin/staff", headers=headers).status_code == 403
    assert client.get("/admin/audit", headers=headers).status_code == 403
    assert client.post("/admin/staff", headers=headers, json={"staff_id": "escalated", "password": PASSWORD}).status_code == 403
    assert client.patch("/admin/staff/" + actor, headers=headers, json={"active": False}).status_code == 403
    assert client.post("/auth/login", json={"mode": "super_admin", "token": identity["token"]}).status_code == 401
    super_login = client.post("/auth/login", json={"mode": "super_admin", "token": " " + support.ADMIN_TOKEN + "\n"})
    assert super_login.status_code == 200
    assert super_login.json()["role"] == "super_admin"
    assert client.get("/admin/me", headers=admin).json()["role"] == "super_admin"


def test_password_reset_and_logout_revoke_sessions():
    actor = create("reset-test")
    old = login(actor).json()["token"]
    headers = {"Authorization": "Bearer " + old}
    assert client.patch("/admin/staff/" + actor, headers=admin, json={"password": "new-staff-password-long"}).status_code == 200
    assert client.get("/admin/me", headers=headers).status_code == 401
    assert login(actor).status_code == 401
    new = login(actor, "new-staff-password-long").json()["token"]
    headers = {"Authorization": "Bearer " + new}
    assert client.post("/admin/logout", headers=headers).status_code == 200
    assert client.get("/admin/me", headers=headers).status_code == 401


def test_password_and_session_storage_are_hashed_and_audit_has_no_secrets():
    actor = create("storage-test")
    token = login(actor).json()["token"]
    with support.connect() as conn:
        stored = conn.execute("SELECT password_hash FROM staff_accounts WHERE id=?", (actor,)).fetchone()[0]
        assert stored != PASSWORD and support.password_matches(PASSWORD, stored)
        assert not support.password_matches("wrong-password", stored)
        row = conn.execute("SELECT token_hash FROM staff_sessions WHERE staff_id=?", (actor,)).fetchone()
        assert row[0] == hashlib.sha256(token.encode()).hexdigest()
    response = client.get("/admin/staff", headers=admin)
    assert stored not in response.text and PASSWORD not in response.text
    audit = client.get("/admin/audit", headers=admin, params={"actor": actor}).text
    assert "auth.login" in audit and PASSWORD not in audit and token not in audit


def test_expired_and_disabled_accounts_cannot_authenticate():
    actor = create("expiry-test")
    token = login(actor).json()["token"]
    with support.connect() as conn:
        conn.execute("UPDATE staff_sessions SET expires=? WHERE staff_id=?", (time.time() - 1, actor))
    assert client.get("/admin/me", headers={"Authorization": "Bearer " + token}).status_code == 401
    client.patch("/admin/staff/" + actor, headers=admin, json={"active": False})
    assert login(actor).status_code == 401
    client.patch("/admin/staff/" + actor, headers=admin, json={"active": True})
    assert login(actor).status_code == 200


def test_invalid_duplicate_and_reserved_accounts_are_rejected():
    create("duplicate-test")
    assert client.post("/admin/staff", headers=admin, json={"staff_id": "DUPLICATE-TEST", "password": PASSWORD}).status_code == 409
    for actor in ("super-admin", "anonymous", "shared-token", "contains spaces"):
        assert client.post("/admin/staff", headers=admin, json={"staff_id": actor, "password": PASSWORD}).status_code == 422
    assert client.post("/admin/staff", headers=admin, json={"staff_id": "weak-test", "password": "short"}).status_code == 422
    assert client.patch("/admin/staff/missing-test", headers=admin, json={"active": False}).status_code == 404


def test_failed_login_attempts_are_throttled_and_audited():
    for _ in range(5):
        assert login("unknown-rate-test", "wrong").status_code == 401
    assert login("unknown-rate-test", "wrong").status_code == 429
    rows = client.get("/admin/audit", headers=admin, params={"action": "auth.login_failed"}).json()["entries"]
    assert any(row["resource"] == "unknown-rate-test" and row["outcome"] == "denied" for row in rows)
    assert "wrong" not in json.dumps(rows)
