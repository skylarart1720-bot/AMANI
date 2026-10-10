"""Exercise production servers at mobile, tablet and desktop sizes."""
import json
import os
import re
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from browser_safety import install_secret_redaction
install_secret_redaction()
expect.set_options(timeout=20000)

ROOT = Path(__file__).resolve().parents[1]
services = {item["name"]: item["url"] for item in json.loads((ROOT / ".runtime/services.json").read_text())}
artifacts = ROOT / "artifacts"
artifacts.mkdir(exist_ok=True)

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(services["web"], wait_until="domcontentloaded")
    expect(page.get_by_text("Support service connected", exact=True)).to_be_visible(timeout=30000)
    for width, height in [(320, 740), (360, 800), (390, 844), (768, 1024), (1024, 900), (1440, 1000), (1920, 1080), (3440, 1440)]:
        page.set_viewport_size({"width": width, "height": height})
        page.screenshot(path=str(artifacts / f"support-{width}.png"), full_page=True)
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"Overflow at {width}px"
        expect(page.get_by_role("button", name="Quick exit")).to_be_visible()
        expect(page.get_by_role("textbox", name="Your message")).to_be_visible()
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.get_by_role("textbox", name="Your message").fill("I need support with online safety")
    page.get_by_role("button", name="Send message", exact=True).click()
    expect(page.locator(".message.assistant")).to_have_count(1, timeout=40000)
    expect(page.get_by_text("Directory response", exact=True)).to_be_visible()
    page.get_by_role("button", name="Request human support", exact=True).click()
    page.get_by_role("button", name="Join general queue", exact=True).click()
    expect(page.locator(".case-status")).to_be_visible()
    case_id = re.search(r'A-[A-F0-9]+', page.locator('.case-status').inner_text()).group(0)
    page.screenshot(path=str(artifacts / "conversation.png"), full_page=True)

    moderator = browser.new_page(viewport={"width": 1440, "height": 1000})
    moderator.goto(services["moderator"])
    token = os.getenv("ADMIN_API_TOKEN") or (ROOT / "data/.admin-token").read_text().strip()
    moderator.get_by_label("Sign in as").select_option("super_admin")
    moderator.get_by_label("Super Admin token").fill(token)
    moderator.get_by_role("button", name="Sign in", exact=True).click()
    expect(moderator.get_by_role("heading", name="Support operations")).to_be_visible()
    moderator.locator(".case").filter(has_text=case_id).click()
    moderator.get_by_label("Reply to visitor").fill("Browser test: a human moderator reply.")
    moderator.get_by_role("button", name="Send reply", exact=True).click()
    expect(page.locator(".message.human")).to_contain_text("human moderator reply", timeout=20000)
    page.get_by_role("textbox", name="Your message").fill("Thank you, I am here.")
    page.get_by_role("button", name="Send message", exact=True).click()
    expect(moderator.get_by_text("Thank you, I am here.", exact=True)).to_be_visible(timeout=20000)
    expect(page.locator(".message.assistant")).to_have_count(1)
    moderator.screenshot(path=str(artifacts / "moderator-desktop.png"), full_page=True)
    moderator.set_viewport_size({"width": 390, "height": 844})
    assert moderator.evaluate("document.documentElement.scrollWidth <= innerWidth")
    moderator.screenshot(path=str(artifacts / "moderator-mobile.png"), full_page=True)

    for width, height in [(390, 844), (768, 1024), (1440, 1000)]:
        page.set_viewport_size({"width": width, "height": height})
        for view in ["Support topics", "Find help", "Check a link"]:
            if width < 700:
                page.get_by_role("button", name="Toggle navigation").click()
            page.get_by_role("navigation", name="Main navigation").get_by_role("button", name=view, exact=True).click()
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"Overflow in {view} at {width}px"
            page.screenshot(path=str(artifacts / f"{view.replace(' ', '-').lower()}-{width}.png"), full_page=True)
    page.get_by_label("Website URL", exact=True).fill("https://example.com")
    page.get_by_role("checkbox").check()
    page.get_by_role("button", name="Check link", exact=True).click()
    expect(page.locator(".verdict")).to_be_visible(timeout=20000)
    page.get_by_role("navigation", name="Main navigation").get_by_role("button", name="Find help", exact=True).click()
    page.get_by_role("textbox", name="Search organisations").fill("Cyber")
    expect(page.locator(".directory-grid .referral")).to_have_count(1)
    page.get_by_role("button", name="Delete conversation", exact=True).click()
    page.get_by_role("dialog").get_by_role("button", name="Delete conversation", exact=True).click()
    expect(page.get_by_text("Your conversation has been deleted from this service.", exact=True)).to_be_visible()
    assert not page.evaluate("sessionStorage.getItem('amani-session')")
    expect(moderator.locator(".case").filter(has_text=case_id)).to_have_count(0, timeout=20000)
    page.get_by_label("Language / Langue").select_option("fr")
    expect(page.get_by_role("heading", name="Trouvez un point de soutien.")).to_be_visible()
    for width in (320, 360, 390, 768, 1440):
        page.set_viewport_size({"width": width, "height": 900})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"French overflow at {width}px"
        page.screenshot(path=str(artifacts / f"french-directory-{width}.png"), full_page=True)
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.get_by_role("navigation", name="Navigation principale").get_by_role("button", name="Obtenir du soutien", exact=True).click()
    page.get_by_role("textbox", name="Votre message").fill("Je cherche du soutien pour mon anxiété")
    page.get_by_role("button", name="Envoyer le message", exact=True).click()
    expect(page.locator(".message.assistant")).to_contain_text("Je peux vous aider", timeout=40000)
    page.get_by_role("button", name="Supprimer la conversation", exact=True).first.click()
    page.get_by_role("dialog").get_by_role("button", name="Supprimer la conversation", exact=True).click()
    expect(page.get_by_text("Votre conversation a été supprimée de ce service.", exact=True)).to_be_visible()
    assert not errors, errors
    browser.close()
print("PASS: 8 screen sizes, 3 feature views, chat, live moderator reply, directory search, URL check, deletion, French interface and French support; no page errors.")
