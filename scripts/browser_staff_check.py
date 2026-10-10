"""Check local administrator/staff workflows with one temporary synthetic account."""
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
    services = {item["name"]: item["url"] for item in json.loads((ROOT / ".runtime/services.json").read_text())}
    url = services["moderator"]
    if urlsplit(url).hostname not in ("localhost", "127.0.0.1"):
        raise ValueError("This workflow only runs against the local stack")
    env = dotenv_values(ROOT / ".env")
    token = env.get("ADMIN_API_TOKEN") or (ROOT / "data/.admin-token").read_text().strip()
    actor = "ui-test-" + secrets.token_hex(6)
    password = secrets.token_urlsafe(24)
    replacement = secrets.token_urlsafe(24)
    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            admin = browser.new_page(viewport={"width": 1440, "height": 1000})
            admin.on("pageerror", lambda error: errors.append(str(error)))
            admin.goto(url)
            admin.get_by_label("Sign in as").select_option("super_admin")
            admin.get_by_label("Super Admin token").fill(token)
            admin.get_by_role("button", name="Sign in", exact=True).click()
            expect(admin.get_by_role("heading", name="Support operations")).to_be_visible()
            admin.get_by_role("button", name="Staff accounts", exact=True).click()
            admin.get_by_label("New staff ID").fill(actor)
            admin.get_by_label("Password", exact=False).fill(password)
            admin.get_by_role("button", name="Create staff", exact=True).click()
            row = admin.get_by_role("row").filter(has_text=actor)
            expect(row).to_be_visible()
            for width in (390, 768, 1440):
                admin.set_viewport_size({"width": width, "height": 1000})
                assert admin.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"Overflow at {width}px"
            staff = browser.new_page(viewport={"width": 390, "height": 844})
            staff.on("pageerror", lambda error: errors.append(str(error)))
            staff.goto(url)
            staff.get_by_label("Staff ID", exact=True).fill(actor.upper())
            staff.get_by_label("Password", exact=True).fill(password)
            staff.get_by_role("button", name="Sign in", exact=True).click()
            expect(staff.get_by_role("heading", name="Support operations")).to_be_visible()
            expect(staff.get_by_role("button", name="Staff accounts", exact=True)).to_have_count(0)
            expect(staff.get_by_role("button", name="Audit log", exact=True)).to_have_count(0)
            assert staff.request.get(url + "/api/admin/staff").status == 403
            assert staff.request.get(url + "/api/admin/audit").status == 403
            row.get_by_role("button", name="Reset password", exact=True).click()
            admin.get_by_label("New password for " + actor).fill(replacement)
            admin.get_by_role("button", name="Reset password", exact=True).first.click()
            expect(admin.get_by_role("status")).to_contain_text("Password reset")
            staff.reload()
            expect(staff.get_by_role("heading", name="Moderator sign in")).to_be_visible()
            staff.get_by_label("Staff ID", exact=True).fill(actor)
            staff.get_by_label("Password", exact=True).fill(replacement)
            staff.get_by_role("button", name="Sign in", exact=True).click()
            expect(staff.get_by_role("heading", name="Support operations")).to_be_visible()
            row.get_by_role("button", name="Disable", exact=True).click()
            expect(row).to_contain_text("Disabled")
            staff.reload()
            expect(staff.get_by_role("heading", name="Moderator sign in")).to_be_visible()
            row.get_by_role("button", name="View activity", exact=True).click()
            expect(admin.get_by_role("heading", name="Staff audit log")).to_be_visible()
            expect(admin.get_by_role("cell", name="auth.login", exact=True).first).to_be_visible()
            admin.get_by_role("button", name="Sign out", exact=True).click()
            expect(admin.get_by_role("heading", name="Moderator sign in")).to_be_visible()
            browser.close()
        assert not errors, errors
        print("PASS: login choice, super admin creation, staff login, role restrictions, password reset, disable/revocation, audit view, logout and three screen widths")
    finally:
        # Only this run's randomly named synthetic account is removed.
        with sqlite3.connect(ROOT / "data/support.db") as conn:
            conn.execute("DELETE FROM staff_sessions WHERE staff_id=?", (actor,))
            conn.execute("DELETE FROM staff_accounts WHERE id=?", (actor,))


if __name__ == "__main__":
    main()
