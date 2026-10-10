import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from browser_safety import install_secret_redaction
install_secret_redaction()
import httpx
import os
from dotenv import dotenv_values
from playwright.sync_api import sync_playwright, expect

root = Path(__file__).resolve().parents[1]
web = os.getenv('AMANI_TEST_WEB','http://127.0.0.1:3000')
admin = os.getenv('AMANI_TEST_ADMIN','http://127.0.0.1:3100')
token = dotenv_values(root / '.env')['ADMIN_API_TOKEN']
visitor = httpx.Client(timeout=40)
moderator = httpx.Client(timeout=40)
def checked(response):
    assert response.status_code == 200, response.status_code
    return response.json()
checked(moderator.post(admin+'/api/login', json={'mode':'super_admin','token':token}))
session = checked(visitor.post(web+'/api/support/sessions'))['token']
visitor.headers['Authorization'] = 'Bearer '+session
try:
    chat = checked(visitor.post(web+'/api/support/chat',json={'message':'Synthetic deployment check: where can I find online safety support?', 'ai_consent':False}))
    assert chat['reply']
    case = checked(visitor.post(web+'/api/support/handoff',json={}))['id']
    checked(moderator.post(admin+'/api/admin/queue/'+case+'/notes',json={'content':'Synthetic private note; must never reach visitor.'}))
    assert checked(moderator.get(admin+'/api/admin/queue/'+case+'/notes'))['notes']
    assert 'Synthetic private note' not in visitor.get(web+'/api/support/messages').text
    checked(moderator.post(admin+'/api/admin/queue/'+case+'/transfer',json={'staff_id':'super-admin'}))
    checked(moderator.post(admin+'/api/admin/queue/'+case+'/reply',json={'message':'Synthetic deployment check: human reply delivered.'}))
    history = checked(visitor.get(web+'/api/support/messages'))
    assert any(m['content']=='Synthetic deployment check: human reply delivered.' for m in history['messages'])
    checked(moderator.patch(admin+'/api/admin/queue/'+case,json={'status':'resolved'}))
    checked(moderator.patch(admin+'/api/admin/queue/'+case,json={'status':'queued'}))
    checked(moderator.post(admin+'/api/admin/presence',json={'status':'busy'}))
    assert 'super-admin' not in {x['id'] for x in checked(visitor.get(web+'/api/support/staff'))['staff']}
    assert checked(moderator.get(admin+'/api/admin/activity'))['staff']
    checked(moderator.post(admin+'/api/admin/presence',json={'status':'offline'}))
    print('PASS: hosted chat, handoff and human reply')
finally:
    checked(visitor.delete(web+'/api/support/sessions'))
    checked(moderator.post(admin+'/api/logout'))
    print('PASS: synthetic conversation deleted and moderator logged out')

with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge',headless=True)
    page = browser.new_page()
    errors=[]
    page.on('pageerror',lambda e: errors.append(str(e)))
    page.goto(web,wait_until='domcontentloaded')
    expect(page.get_by_text('Support service connected',exact=True)).to_be_visible(timeout=40000)
    assert page.get_by_label('Language / Langue').locator('option').count()==24
    for width in (390,768,1440):
        page.set_viewport_size({'width':width,'height':900})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.goto(admin,wait_until='domcontentloaded')
    page.get_by_label('Sign in as').select_option('super_admin')
    page.get_by_label('Super Admin token').fill(token)
    page.get_by_role('button',name='Sign in',exact=True).click()
    expect(page.get_by_role('heading',name='Support operations')).to_be_visible(timeout=40000)
    page.get_by_label('Availability',exact=True).select_option('busy')
    page.get_by_role('button',name='Staff activity',exact=True).click()
    expect(page.get_by_role('heading',name='Staff activity',exact=True)).to_be_visible()
    for width in (390,768,1440):
        page.set_viewport_size({'width':width,'height':900})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert not errors
    assert page.request.post(admin+'/api/logout').status == 200
    browser.close()
print('PASS: live mobile layouts, 24 languages, browser Super Admin login; no page errors')
