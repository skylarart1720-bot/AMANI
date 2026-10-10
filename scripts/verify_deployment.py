"""Read-only deployment checks. Never submits credentials or conversation data."""
import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


async def verify(web, moderator):
    checks = []
    async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
        async def get(name, origin, path, expected):
            try:
                response = await client.get(origin.rstrip("/") + path)
                checks.append({"name": name, "status": response.status_code,
                               "passed": response.status_code == expected})
                return response
            except httpx.HTTPError as error:
                checks.append({"name": name, "passed": False,
                               "error": type(error).__name__})
                return None

        await get("public HTTPS page", web, "/", 200)
        await get("moderator HTTPS page", moderator, "/", 200)
        status = await get("support status", web, "/api/support/status", 200)
        if status is not None and status.status_code == 200:
            try:
                checks[-1]["configuration"] = status.json()
            except ValueError:
                checks[-1]["passed"] = False
        directory = await get("directory", web, "/api/support/directory", 200)
        filtered = await get("region query forwarding", web,
                             "/api/support/directory?region=Ghana", 200)
        if directory is not None and filtered is not None:
            try:
                all_rows = directory.json()["referrals"]
                ghana = filtered.json()["referrals"]
                checks.append({"name": "region filter semantics", "passed":
                               bool(ghana) and len(ghana) < len(all_rows)
                               and all("Ghana" in row.get("regions", []) for row in ghana),
                               "total": len(all_rows), "filtered": len(ghana)})
                checks.append({"name": "referral verification fields", "passed":
                               bool(all_rows) and all("verification" in row for row in all_rows)})
            except (ValueError, KeyError, TypeError):
                checks.append({"name": "directory response shape", "passed": False})
        await get("moderator audit authentication", moderator, "/api/admin/audit", 401)
        await get("moderator rejects public routes", moderator, "/api/support/status", 404)
        await get("public rejects admin routes", web, "/api/admin/audit", 404)
    return {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "web": web, "moderator": moderator, "checks": checks,
            "limitations": ["No production data or credentials submitted.",
                            "Response fingerprints do not prove a deployed commit SHA.",
                            "Database, persistence, staff identities and streaming require host access."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--web", default="https://amani-navy.vercel.app")
    parser.add_argument("--moderator", default="https://amani-hck2.vercel.app")
    parser.add_argument("--output", default=str(ROOT / "artifacts/deployment-verification.json"))
    args = parser.parse_args()
    report = asyncio.run(verify(args.web, args.moderator))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    for check in report["checks"]:
        print(("PASS" if check["passed"] else "FAIL") + ": " + check["name"])
    print("Report: " + str(output))
    raise SystemExit(0 if all(check["passed"] for check in report["checks"]) else 1)


if __name__ == "__main__":
    main()
