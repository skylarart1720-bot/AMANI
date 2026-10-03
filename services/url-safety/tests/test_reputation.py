import importlib.util
from pathlib import Path
from unittest.mock import patch
import httpx
import pytest
import asyncio
import time
from fastapi.testclient import TestClient

spec = importlib.util.spec_from_file_location("url_service", Path(__file__).resolve().parents[1] / "src/main.py")
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)
client = TestClient(service.app)

@pytest.fixture(autouse=True)
def isolated_configuration(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    service._analyses.clear()
    service._cache.clear()
    service._analysis_lock = asyncio.Lock()

@pytest.mark.parametrize("missing", [False, True])
def test_stale_or_missing_report_starts_scan_then_completes(missing):
    calls = []
    def handle(request):
        calls.append((request.method, request.url.path))
        if request.method == "POST":
            return httpx.Response(200, json={"data": {"id": "analysis-123"}})
        if "/analyses/" in request.url.path:
            return httpx.Response(200, json={"data": {"attributes": {"status": "completed", "stats": {"malicious": 2, "harmless": 30}}}})
        return httpx.Response(404 if missing else 200, json={"data": {"attributes": {"last_analysis_date": 1, "last_analysis_stats": {"harmless": 30}}}})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
            result = await service.virustotal_lookup(http, "https://example.com/", "test-key")
            assert result["status"] == "pending"
            assert (await service.virustotal_lookup(http, "https://example.com/", "test-key"))["status"] == "pending"
            assert len(calls) == 2
            next(iter(service._analyses.values()))["next_poll"] = 0
            result = await service.virustotal_lookup(http, "https://example.com/", "test-key")
            assert result["status"] == "flagged"
            assert result["detections"] == 2
    asyncio.run(run())

def test_fresh_report_does_not_submit_and_quota_is_explicit():
    async def run():
        def fresh(request):
            assert request.method == "GET"
            return httpx.Response(200, json={"data": {"attributes": {"last_analysis_date": time.time(), "last_analysis_stats": {"harmless": 30}}}})
        async with httpx.AsyncClient(transport=httpx.MockTransport(fresh)) as http:
            assert (await service.virustotal_lookup(http, "https://example.com/", "test-key"))["status"] == "no_known_threats"
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(429))) as http:
            assert (await service.virustotal_lookup(http, "https://example.com/", "test-key"))["status"] == "rate_limited"
    asyncio.run(run())

@pytest.mark.parametrize("url", ["file:///etc/passwd", "http://127.0.0.1/", "http://localhost", "http://10.0.0.1", "https://user:password@example.com", "https://example.com:8080", "https://evil\\@example.com", "http://[::1]", "javascript:alert(1)"])
def test_rejects_private_or_ambiguous_urls(url):
    assert client.post("/check", json={"url": url, "consent": True}).status_code == 400

def test_consent_and_unknown_without_providers(monkeypatch):
    monkeypatch.delenv("SAFE_BROWSING_API_KEY", raising=False)
    monkeypatch.delenv("VIRUSTOTAL_API_KEY", raising=False)
    assert client.post("/check", json={"url": "https://example.com"}).status_code == 400
    result = client.post("/check", json={"url": "https://example.com", "consent": True}).json()
    assert result["verdict"] == "unknown"
    assert result["safe"] is None
    assert "score" not in result
    assert client.post('/check', json={'url': 'http://example.com:443/', 'consent': True}).status_code == 400
    assert client.post('/check', json={'url': 'https://example.com:80/', 'consent': True}).status_code == 400

def test_google_flagged_and_failure(monkeypatch):
    monkeypatch.setenv("SAFE_BROWSING_API_KEY", "test-key")
    monkeypatch.delenv("VIRUSTOTAL_API_KEY", raising=False)
    async def flagged(*args, **kwargs):
        return httpx.Response(200, json={"matches": [{"threatType": "MALWARE"}]}, request=httpx.Request("POST", "https://safebrowsing.googleapis.com"))
    with patch.object(httpx.AsyncClient, "post", flagged):
        assert client.post("/check", json={"url": "https://example.com", "consent": True}).json()["verdict"] == "flagged"
    async def failed(*args, **kwargs):
        raise httpx.ReadTimeout("provider timeout")
    with patch.object(httpx.AsyncClient, "post", failed):
        assert client.post("/check", json={"url": "https://example.com", "consent": True}).json()["verdict"] == "unknown"
