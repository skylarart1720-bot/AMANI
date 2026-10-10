"""Verify local availability, chosen-staff conversations and unfinished-feature visibility."""
import json
import secrets
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values
from playwright.sync_api import expect, sync_playwright
from browser_safety import install_secret_redaction
install_secret_redaction()

ROOT = Path(__file__).resolve().parents[1]


def main():
    expect.set_options(timeout=20000)
    services = {item["name"]: item["url"] for item in json.loads((ROOT / ".runtime/services.json").read_text())}
    if any(urlsplit(services[name]).hostname not in ("localhost", "127.0.0.1") for name in ("web", "moderator")):
        raise ValueError("Only the local stack may be used")
    admin_token = dotenv_values(ROOT / ".env").get("ADMIN_API_TOKEN") or (ROOT / "data/.admin-token").read_text().strip()
    actor = "presence-ui-" + secrets.token_hex(5)
    password = secrets.token_urlsafe(24)
    visitor_token = None
    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            admin = browser.new_page(viewport={"width": 1440, "height": 1000})
            admin.on("pageerror", lambda error: errors.append(str(error)))
            admin.goto(services["moderator"])
            admin.get_by_label("Sign in as").select_option("super_admin")
            admin.get_by_label("Super Admin token").fill(admin_token)
            admin.get_by_role("button", name="Sign in", exact=True).click()
            expect(admin.get_by_role("heading", name="Support operations")).to_be_visible()
            expect(admin.get_by_role("button", name="Online", exact=True)).to_be_visible()
            response = admin.request.post(services["moderator"] + "/api/admin/staff", data={"staff_id": actor, "password": password})
            assert response.status == 200
            staff = browser.new_page(viewport={"width": 1440, "height": 1000})
            staff.on("pageerror", lambda error: errors.append(str(error)))
            staff.goto(services["moderator"])
            staff.get_by_label("Staff ID", exact=True).fill(actor)
            staff.get_by_label("Password", exact=True).fill(password)
            staff.get_by_role("button", name="Sign in", exact=True).click()
            expect(staff.get_by_role("button", name="Online", exact=True)).to_be_visible()
            visitor = browser.new_page(viewport={"width": 1440, "height": 1000})
            visitor.on("pageerror", lambda error: errors.append(str(error)))
            visitor.goto(services["web"])
            picker = visitor.get_by_role("region", name="Online human support")
            expect(picker.get_by_role("button").filter(has_text=actor)).to_be_visible(timeout=20000)
            expect(picker.get_by_role("button").filter(has_text="Super Admin")).to_be_visible()
            visitor.get_by_role("button", name="Request human support", exact=True).click()
            picker.get_by_role("button").filter(has_text=actor).click()
            expect(visitor.locator(".case-status")).to_contain_text(actor)
            visitor_token = visitor.evaluate("sessionStorage.getItem('amani-session')")
            visitor.get_by_role("textbox", name="Your message").fill("Synthetic check: I chose this support person.")
            visitor.get_by_role("button", name="Send message", exact=True).click()
            expect(visitor.get_by_text("Message sent to human support.", exact=True)).to_be_visible(timeout=20000)
            queue = staff.request.get(services["moderator"] + "/api/admin/queue").json()
            case = next(row for row in queue if row["assignee"] == actor)
            expect(staff.locator(".case").filter(has_text=case["id"])).to_be_visible(timeout=20000)
            staff.locator(".case").filter(has_text=case["id"]).click()
            staff.get_by_label("Reply to visitor").fill("Synthetic staff reply received.")
            staff.get_by_role("button", name="Send reply", exact=True).click()
            expect(visitor.locator(".message.human")).to_contain_text("Synthetic staff reply received.", timeout=20000)
            staff.get_by_role("button", name="Online", exact=True).click()
            expect(staff.get_by_role("button", name="Offline", exact=True)).to_be_visible()
            expect(picker.get_by_role("button").filter(has_text=actor)).to_have_count(0, timeout=20000)
            artifacts = ROOT / "artifacts"
            artifacts.mkdir(exist_ok=True)
            for width in (390, 768, 1440):
                visitor.set_viewport_size({"width": width, "height": 1000})
                assert visitor.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"Web overflow at {width}"
            visitor.get_by_role("navigation").get_by_role("button", name="WhatsApp", exact=True).click()
            expect(visitor.get_by_role("heading", name="AMANI on WhatsApp")).to_be_visible()
            expect(visitor.get_by_text("Setup pending", exact=True)).to_be_visible()
            visitor.screenshot(path=str(artifacts / "whatsapp-pending.png"), full_page=True)
            admin.get_by_role("button", name="Setup & integrations", exact=True).click()
            expect(admin.get_by_role("heading", name="Setup & integrations")).to_be_visible()
            expect(admin.get_by_role("heading", name="WhatsApp", exact=True)).to_be_visible()
            expect(admin.get_by_role("heading", name="MFA and organisation isolation")).to_be_visible()
            for width in (390, 768, 1440):
                admin.set_viewport_size({"width": width, "height": 1000})
                assert admin.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"Admin overflow at {width}"
            admin.screenshot(path=str(artifacts / "setup-integrations.png"), full_page=True)
            admin.get_by_role("button", name="Sign out", exact=True).click()
            staff.get_by_role("button", name="Sign out", exact=True).click()
            browser.close()
        assert not errors, errors
        print("PASS: staff/admin presence, chosen-person assignment, human reply round-trip, offline removal, WhatsApp pending page, setup checklist and responsive layouts")
    finally:
        with sqlite3.connect(ROOT / "data/support.db") as conn:
            conn.execute("PRAGMA foreign_keys=ON")
            if visitor_token:
                import hashlib
                conn.execute("DELETE FROM sessions WHERE id=?", (hashlib.sha256(visitor_token.encode()).hexdigest(),))
            conn.execute("DELETE FROM staff_presence WHERE actor=?", (actor,))
            conn.execute("DELETE FROM staff_sessions WHERE staff_id=?", (actor,))
            conn.execute("DELETE FROM staff_accounts WHERE id=?", (actor,))


if __name__ == "__main__":
    main()
