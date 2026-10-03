"""Reputation lookups never visit the submitted URL or claim a URL is safe."""
import asyncio
import base64
import ipaddress
import os
import re
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import dotenv_values

app = FastAPI(title="Amani Line URL Reputation", version="1.0.0")
_configuration_mtime = None
_cache = {}
_analyses = {}
_analysis_lock = asyncio.Lock()

def refresh_configuration():
    global _configuration_mtime
    root = Path(__file__).resolve()
    env_file = root.parents[3] / ".env" if len(root.parents) > 3 else Path("/app/.env")
    if not env_file.exists() or os.getenv("APP_ENV") in ("production", "test"):
        return
    modified = env_file.stat().st_mtime_ns
    if modified != _configuration_mtime:
        values = dotenv_values(env_file)
        for name in ("SAFE_BROWSING_API_KEY", "VIRUSTOTAL_API_KEY"):
            if name in values:
                os.environ[name] = values[name] or ""
        _configuration_mtime = modified


class UrlCheckRequest(BaseModel):
    url: str = Field(min_length=1, max_length=4096)
    consent: bool = False


def normalize_url(value: str) -> str:
    try:
        if re.search(r"[\s\\\x00-\x1f\x7f]", value):
            raise ValueError()
        parsed = urlsplit(value)
        host = (parsed.hostname or "").encode("idna").decode("ascii").lower().rstrip(".")
        if parsed.scheme not in ("http", "https") or not host or parsed.username or parsed.password:
            raise ValueError()
        if parsed.port not in (None, 443 if parsed.scheme == "https" else 80):
            raise ValueError()
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None:
            if not address.is_global:
                raise ValueError()
            host = f"[{host}]" if address.version == 6 else host
        elif ("." not in host or host.endswith((".localhost", ".local", ".internal", ".test", ".invalid"))
              or not re.fullmatch(r"[a-z0-9.-]+", host)
              or any(not part or part.startswith("-") or part.endswith("-") for part in host.split("."))):
            raise ValueError()
        return urlunsplit((parsed.scheme, host, parsed.path or "/", parsed.query, ""))
    except (ValueError, UnicodeError):
        raise HTTPException(400, "Enter a public HTTP or HTTPS URL without credentials or a custom port.")


async def google_lookup(client: httpx.AsyncClient, url: str, key: str) -> dict:
    try:
        response = await client.post("https://safebrowsing.googleapis.com/v4/threatMatches:find", params={"key": key}, json={
            "client": {"clientId": "amani-line", "clientVersion": "1.0"},
            "threatInfo": {"threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"],
                           "platformTypes": ["ANY_PLATFORM"], "threatEntryTypes": ["URL"], "threatEntries": [{"url": url}]},
        })
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or "error" in data:
            raise ValueError()
        return {"provider": "Google Safe Browsing", "status": "flagged" if data.get("matches") else "no_known_threats"}
    except (httpx.HTTPError, ValueError):
        return {"provider": "Google Safe Browsing", "status": "unavailable"}


async def virustotal_lookup(client: httpx.AsyncClient, url: str, key: str) -> dict:
    url_id = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
    digest = hashlib.sha256((url + key).encode()).hexdigest()
    headers = {"x-apikey": key}
    def outcome(stats):
        if not isinstance(stats, dict) or not any(isinstance(n, int) and n > 0 for n in stats.values()):
            return {"provider": "VirusTotal", "status": "unknown"}
        flagged = stats.get("malicious", 0) + stats.get("suspicious", 0)
        return {"provider": "VirusTotal", "status": "flagged" if flagged else "no_known_threats", "detections": flagged}
    try:
        # Deduplicate submissions and throttle polling against the provider quota.
        async with _analysis_lock:
            now = time.monotonic()
            for old in [k for k, v in _analyses.items() if now - v["created"] > 3600]:
                del _analyses[old]
            job = _analyses.get(digest)
            if job:
                if now < job["next_poll"]:
                    return job["result"]
                job["next_poll"] = now + 20
                response = await client.get(f"https://www.virustotal.com/api/v3/analyses/{job['id']}", headers=headers)
                response.raise_for_status()
                attributes = response.json()["data"]["attributes"]
                if attributes.get("status") == "completed":
                    job["result"] = outcome(attributes.get("stats"))
                    job["next_poll"] = now + 300
                return job["result"]
            response = await client.get(f"https://www.virustotal.com/api/v3/urls/{url_id}", headers=headers)
            if response.status_code != 404:
                response.raise_for_status()
                attributes = response.json()["data"]["attributes"]
                result = outcome(attributes.get("last_analysis_stats"))
                if datetime.now(timezone.utc).timestamp() - attributes.get("last_analysis_date", 0) <= 86400 * 7 and result["status"] != "unknown":
                    return result
            response = await client.post("https://www.virustotal.com/api/v3/urls", headers=headers, data={"url": url})
            response.raise_for_status()
            analysis_id = response.json()["data"]["id"]
            if not isinstance(analysis_id, str) or not re.fullmatch(r"[A-Za-z0-9_=-]+", analysis_id):
                raise ValueError()
            result = {"provider": "VirusTotal", "status": "pending"}
            if len(_analyses) >= 1000:
                _analyses.pop(next(iter(_analyses)))
            _analyses[digest] = {"id": analysis_id, "created": now, "next_poll": now + 20, "result": result}
            return result
    except httpx.HTTPStatusError as error:
        return {"provider": "VirusTotal", "status": "rate_limited" if error.response.status_code == 429 else "unavailable"}
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return {"provider": "VirusTotal", "status": "unavailable"}


@app.get("/health")
def health():
    refresh_configuration()
    return {"status": "ok", "configured": bool(os.getenv("SAFE_BROWSING_API_KEY") or os.getenv("VIRUSTOTAL_API_KEY"))}


@app.post("/check")
async def check_url(request: UrlCheckRequest):
    refresh_configuration()
    url = normalize_url(request.url.strip())
    if not request.consent:
        raise HTTPException(400, "Consent is required to share this URL with reputation providers.")
    cache_key = hashlib.sha256((url + os.getenv('SAFE_BROWSING_API_KEY', '') + os.getenv('VIRUSTOTAL_API_KEY', '')).encode()).hexdigest()
    cached = _cache.get(cache_key) if os.getenv('APP_ENV') != 'test' else None
    if cached and cached[0] > time.monotonic():
        return {**cached[1], 'url': url, 'cached': True}
    providers = []
    if os.getenv("SAFE_BROWSING_API_KEY") or os.getenv("VIRUSTOTAL_API_KEY"):
        async with httpx.AsyncClient(timeout=10, follow_redirects=False, trust_env=False) as client:
            tasks = []
            if os.getenv("SAFE_BROWSING_API_KEY"):
                tasks.append(google_lookup(client, url, os.environ["SAFE_BROWSING_API_KEY"]))
            if os.getenv("VIRUSTOTAL_API_KEY"):
                tasks.append(virustotal_lookup(client, url, os.environ["VIRUSTOTAL_API_KEY"]))
            providers = await asyncio.gather(*tasks)
    flagged = any(item["status"] == "flagged" for item in providers)
    completed = any(item["status"] == "no_known_threats" for item in providers)
    pending = any(item["status"] == "pending" for item in providers)
    verdict = "flagged" if flagged else "no_known_threats" if completed else "unknown"
    reasons = ["Reputation providers reported a threat. Do not enter personal details." if flagged else
               "No known threats were reported by the responding providers. This does not guarantee safety." if completed else
               "A fresh analysis is in progress. This link has not been verified yet." if pending else
               "The provider request limit was reached. Please try again later; this link has not been verified." if any(item["status"] == "rate_limited" for item in providers) else
               "A current reputation result is unavailable. This link has not been verified."]
    if url.startswith("http:"):
        reasons.append("This URL uses HTTP, which does not encrypt the connection.")
    if "xn--" in urlsplit(url).netloc:
        reasons.append("The domain uses international characters. Check the spelling against the organisation's official address.")
    result = {"verdict": verdict, "safe": None, "reasons": reasons, "providers": providers,
              "checked_at": datetime.now(timezone.utc).isoformat()}
    if verdict != 'unknown' and os.getenv('APP_ENV') != 'test':
        if len(_cache) >= 1000:
            _cache.clear()
        # Only a URL digest is retained; the timestamp remains the actual lookup time.
        _cache[cache_key] = (time.monotonic() + 60, result)
    return {**result, 'url': url, 'cached': False}
