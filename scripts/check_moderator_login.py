"""Check pasted tokens, cookies and wrong-token rejection without printing secrets."""
import json
import os
from pathlib import Path
import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
services = {item["name"]: item["url"] for item in json.loads((ROOT / ".runtime/services.json").read_text())}
token = os.getenv("ADMIN_API_TOKEN") or (ROOT / "data/.admin-token").read_text().strip()
for base in (services["moderator"], services["moderator"].replace("127.0.0.1", "localhost")):
    with httpx.Client(timeout=30, trust_env=False, headers={"Origin": base}) as client:
        response = client.post(base + "/api/login", json={"token": " \n" + token + "\n "})
        assert response.status_code == 200, response.status_code
        assert "HttpOnly" in response.headers["set-cookie"]
        assert client.get(base + "/api/admin/queue").status_code == 200
        assert client.post(base + "/api/logout").status_code == 200
        assert client.get(base + "/api/admin/queue").status_code == 401
        assert client.post(base + "/api/login", json={"token": "invalid-token-with-enough-characters"}).status_code == 401
    print(base + ": pasted token, authenticated queue, logout and invalid token checks PASS")
