"""Exercise offline languages, RTL layout, preserved transcripts and translation consent."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from browser_safety import install_secret_redaction
install_secret_redaction()

ROOT = Path(__file__).resolve().parents[1]
services = {item['name']: item['url'] for item in json.loads((ROOT / '.runtime/services.json').read_text(encoding='utf-8'))}

def main():
    expect.set_options(timeout=20000)
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(services['web'])
        expect(page.get_by_text('Support service connected', exact=True)).to_be_visible()
        selector = page.locator('.language-control select')
        assert selector.locator('option').count() == 24
        selector.select_option('ak')
        expect(page.locator('html')).to_have_attribute('lang','ak')
        expect(page.get_by_role('button', name='Hwehwɛ mmoa', exact=True)).to_be_visible()
        selector.select_option('ar')
        expect(page.locator('html')).to_have_attribute('dir','rtl')
        expect(page.get_by_role('button', name='ابحث عن مساعدة', exact=True)).to_be_visible()
        for width in (390, 768, 1440):
            page.set_viewport_size({'width':width,'height':1000})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'Arabic overflow at {width}'
        page.screenshot(path=str(ROOT/'artifacts/multilingual-arabic.png'),full_page=True)
        selector.select_option('fr')
        expect(page.locator('html')).to_have_attribute('dir','ltr')
        expect(page.get_by_role('button', name="Trouver de l'aide", exact=True)).to_be_visible()
        # Route labels can change with editorial wording, so use tab structure.
        page.locator('.nav-item').nth(2).click()
        expect(page.get_by_role('heading',name='Access Now Digital Security Helpline')).to_be_visible()
        page.locator('.search-input input').fill('sécurité')
        expect(page.get_by_role('heading',name='Access Now Digital Security Helpline')).to_be_visible()
        selector.select_option('en')
        page.locator('.nav-item').first.click()
        page.get_by_label('Your message').fill('I need support with anxiety')
        page.get_by_role('button', name='Send message').click()
        expect(page.locator('.message.assistant').first).to_be_visible()
        original = page.locator('.message.assistant p[data-original-text]').first.inner_text()
        translate = page.get_by_role('button', name='Translate reply',exact=True).first
        expect(translate).to_be_disabled()
        page.get_by_role('checkbox').first.check()
        page.route('**/api/support/translate', lambda route: route.fulfill(status=200, content_type='application/json',body=json.dumps({'translation':'Respuesta traducida de prueba','language':'es'})))
        selector.select_option('es')
        expect(page.locator('.message.assistant p[data-original-text]').first).to_have_text(original)
        translate.click()
        expect(page.get_by_text('Respuesta traducida de prueba', exact=True)).to_be_visible()
        assert page.locator('.message.assistant p[data-original-text]').first.inner_text() == original
        # Remove only this synthetic visitor conversation.
        token = page.evaluate("sessionStorage.getItem('amani-session')")
        if token:
            result = page.request.delete(services['api']+'/support/sessions',headers={'Authorization':'Bearer '+token})
            assert result.status == 200
        admin = browser.new_page(viewport={'width':390,'height':1000})
        admin.on('pageerror', lambda error: errors.append(str(error)))
        admin.goto(services['moderator'])
        admin.get_by_label('Language',exact=True).select_option('fr')
        expect(admin.get_by_role('heading', name='Connexion du personnel',exact=True)).to_be_visible()
        admin.get_by_label('Langue',exact=True).select_option('ar')
        expect(admin.locator('html')).to_have_attribute('dir','rtl')
        assert admin.evaluate('document.documentElement.scrollWidth <= innerWidth')
        admin.screenshot(path=str(ROOT/'artifacts/multilingual-admin.png'),full_page=True)
        browser.close()
    assert not errors, errors
    print('PASS: 24 language choices, offline navigation, French directory, Arabic RTL at 3 widths, transcript preservation, consent-gated reply translation and multilingual staff login')

if __name__ == '__main__': main()
