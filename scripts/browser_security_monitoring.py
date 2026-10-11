"""Local MFA enrollment through dashboard cookies; hosted mode is read-only account checks."""
import os
import sys
import time
import secrets
import sqlite3
from pathlib import Path
import httpx
from dotenv import dotenv_values
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from browser_safety import install_secret_redaction
install_secret_redaction()
sys.path.insert(0,str(ROOT/'apps/orchestrator/src'))
from security import hotp

base=os.getenv('AMANI_TEST_ADMIN','http://127.0.0.1:3100')
token=dotenv_values(ROOT/'.env')['ADMIN_API_TOKEN']
hosted=base.startswith('https://')
admin=httpx.Client(base_url=base,timeout=40)
def checked(r):
    assert r.status_code==200,r.status_code
    return r.json()
checked(admin.post('/api/login',json={'mode':'super_admin','token':token}))
try:
    assert checked(admin.get('/api/admin/mfa'))['enabled'] is False
    result=checked(admin.post('/api/admin/monitoring/check'))
    assert len(result['services'])>=5
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='chrome',headless=True)
        context=browser.new_context()
        context.add_cookies([{'name':c.name,'value':c.value,'url':base} for c in admin.cookies.jar])
        page=context.new_page();page.goto(base)
        page.get_by_role('button',name='Account security',exact=True).click()
        expect(page.get_by_role('heading',name='Account security',exact=True)).to_be_visible()
        page.get_by_role('button',name='Service monitoring',exact=True).click()
        expect(page.get_by_role('heading',name='Failure and recovery alerts')).to_be_visible()
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        browser.close()
    if not hosted:
        actor='mfa-check-'+secrets.token_hex(4);password=secrets.token_urlsafe(24)
        checked(admin.post('/api/admin/staff',json={'staff_id':actor,'password':password}))
        user=httpx.Client(base_url=base,timeout=40)
        try:
            checked(user.post('/api/login',json={'mode':'staff','staff_id':actor,'password':password}))
            secret=checked(user.post('/api/admin/mfa/setup',json={'credential':password}))['secret']
            enrolled=checked(user.post('/api/admin/mfa/confirm',json={'code':hotp(secret,int(time.time()//30))}))
            assert 'token' not in enrolled and len(enrolled['recovery_codes'])==8
            assert checked(user.get('/api/admin/mfa'))['enabled']
            checked(user.post('/api/logout'))
            assert user.post('/api/login',json={'mode':'staff','staff_id':actor,'password':password}).status_code==401
            checked(user.post('/api/login',json={'mode':'staff','staff_id':actor,'password':password,'code':enrolled['recovery_codes'][0]}))
            checked(user.post('/api/admin/mfa/disable',json={'code':enrolled['recovery_codes'][1]}))
            assert checked(user.get('/api/admin/mfa'))['enabled'] is False
        finally:
            user.close()
            data=ROOT/'data' # run_local.py explicitly selects this directory
            with sqlite3.connect(Path(data)/'support.db') as conn:
                conn.execute('DELETE FROM staff_presence WHERE actor=?',(actor,))
                conn.execute('DELETE FROM staff_sessions WHERE staff_id=?',(actor,))
                conn.execute('DELETE FROM mfa_accounts WHERE actor=?',(actor,))
                conn.execute('DELETE FROM staff_accounts WHERE id=?',(actor,))
    print('Security cookie flow, monitoring, account navigation and mobile layout passed.' if not hosted else 'Hosted token login, account security, monitoring and mobile layout passed; owner MFA unchanged.')
finally:
    admin.post('/api/logout');admin.close()
