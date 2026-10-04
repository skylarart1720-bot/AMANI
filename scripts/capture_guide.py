"""Capture public screens and isolated, fictional moderator examples for the guide."""
import ast
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts' / 'user-guide'
OUT.mkdir(parents=True, exist_ok=True)
PUBLIC = 'https://amani-navy.vercel.app/'
ADMIN = 'https://amani-hck2.vercel.app/'

def main():
    report = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page(viewport={'width':1440,'height':1100}, device_scale_factor=1.5)
        for key, url in [('public', PUBLIC), ('admin', ADMIN)]:
            response = page.goto(url, wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(2500)
            report[key] = {'url':url, 'status':response.status, 'title':page.title(), 'headings':page.locator('h1').all_text_contents()}
        page.goto(PUBLIC, wait_until='domcontentloaded')
        page.locator('.brand').wait_for()
        (OUT/'logo.svg').write_text(page.locator('.brand-mark svg').evaluate('(el)=>el.outerHTML'), encoding='utf-8')
        page.locator('.brand').screenshot(path=str(OUT/'logo.png'))
        page.wait_for_timeout(3000)
        report['public']['connection'] = page.locator('.service-status').inner_text()
        report['public']['assistant_status'] = page.locator('.chat-header p').inner_text()
        page.screenshot(path=str(OUT/'public-home.png'), full_page=True)
        page.locator('.chat-tool').screenshot(path=str(OUT/'chat.png'))
        for name, file in [('Support topics','topics'), ('Find help','directory'), ('Check a link','link-check')]:
            page.get_by_role('navigation',name='Main navigation').get_by_role('button',name=name,exact=True).click()
            page.wait_for_timeout(700)
            page.locator('.main-content').screenshot(path=str(OUT/f'{file}.png'))
        page.get_by_role('button',name='Privacy & safeguarding',exact=True).click()
        page.get_by_role('dialog').screenshot(path=str(OUT/'privacy.png'))
        page.get_by_role('button',name='Close dialog').click()
        page.set_viewport_size({'width':390,'height':844})
        page.get_by_role('button',name='Toggle navigation').click()
        page.screenshot(path=str(OUT/'mobile.png'), full_page=True)
        page.close()

        admin = browser.new_page(viewport={'width':1440,'height':1000}, device_scale_factor=1.5)
        admin.goto(ADMIN, wait_until='domcontentloaded')
        admin.get_by_role('heading',name='Moderator sign in').wait_for()
        admin.locator('.login section').screenshot(path=str(OUT/'admin-login.png'))
        admin.close()

        # These responses exist only inside this browser context. No real login,
        # source publication, directory update or conversation is created.
        case = {'id':'A-DEMO01','priority':'normal','status':'in_progress','created':1790899200,
                'messages':[{'id':1,'role':'user','content':'DEMONSTRATION: I would like information about online safety.'},
                            {'id':2,'role':'assistant','content':'You can explore the support directory for official information.'},
                            {'id':3,'role':'human','content':'DEMONSTRATION: Thank you for reaching out. What kind of information would help you?'}]}
        contact = {'id':'demo-support','title':'Example support service','organisation':'Example Support Organisation (fictional)',
                   'category':'digital-rights','region':'Ghana','phone':None,'website':'https://example.com',
                   'notes':'Fictional contact for this guide. Do not use for referrals.','verified_at':None,
                   'hours':'Confirm with organisation','languages':['English']}
        entry = {'id':'abcdef1234','title':'Example online safety source (fictional)','summary':'Demonstration material only. A real entry must be checked against a reliable source before publication.',
                 'category':'digital-rights','source':'Example publisher','source_url':'https://example.com','verified_at':'2026-10-02','status':'pending'}
        context = browser.new_context(viewport={'width':1440,'height':1000}, device_scale_factor=1.5)
        def mock(route):
            path = route.request.url.split('/api/',1)[-1]
            if path == 'admin/events':
                route.abort()
                return
            data = {'admin/queue':[case], 'admin/directory':[contact], 'admin/knowledge':[entry]}.get(path, {'ok':True})
            route.fulfill(status=200, content_type='application/json', body=json.dumps(data))
        context.route('**/api/**', mock)
        demo = context.new_page()
        demo.goto(ADMIN, wait_until='domcontentloaded')
        demo.get_by_role('heading',name='Support operations').wait_for()
        demo.locator('.case').click()
        demo.locator('main.workspace').screenshot(path=str(OUT/'admin-queue.png'))
        demo.get_by_role('button',name='Referral directory',exact=True).click()
        demo.get_by_role('button',name='Edit',exact=True).click()
        demo.locator('main.workspace').screenshot(path=str(OUT/'admin-directory.png'))
        demo.get_by_role('button',name='Knowledge review',exact=True).click()
        demo.locator('main.workspace').screenshot(path=str(OUT/'admin-knowledge.png'))
        browser.close()
    (OUT/'capture-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__ == '__main__':
    main()
