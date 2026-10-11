import base64
import time
import pytest
from test_staff_presence import client,admin,staff
import support
import security

@pytest.fixture(autouse=True)
def cleanup_mfa():
    with support.connect() as conn:
        conn.execute('DELETE FROM mfa_accounts');conn.execute('DELETE FROM admin_sessions')
    yield
    with support.connect() as conn:
        conn.execute('DELETE FROM mfa_accounts');conn.execute('DELETE FROM admin_sessions')

def enroll(headers,credential):
    setup=client.post('/admin/mfa/setup',headers=headers,json={'credential':credential})
    assert setup.status_code==200
    secret=setup.json()['secret']
    code=security.hotp(secret,int(time.time()//30))
    response=client.post('/admin/mfa/confirm',headers=headers,json={'code':code})
    assert response.status_code==200
    return secret,code,response.json()

def test_rfc_4226_and_6238_vectors():
    secret=base64.b32encode(b'12345678901234567890').decode()
    assert security.hotp(secret,0)=='755224'
    assert security.hotp(secret,1,digits=8)=='94287082'
    assert security.hotp(secret,2000000000//30,digits=8)=='69279037'

def test_host_recovery_revokes_admin_sessions_and_is_audited():
    _,_,result=enroll(admin,support.ADMIN_TOKEN)
    session={'Authorization':'Bearer '+result['token']}
    security.reset_super_admin_mfa(support.DATA)
    assert client.get('/admin/me',headers=session).status_code==401
    assert client.get('/admin/me',headers=admin).status_code==200
    with support.connect() as conn:
        assert conn.execute("SELECT 1 FROM audit WHERE action='mfa.host_recovery'").fetchone()

def test_super_admin_requires_factor_and_raw_token_no_longer_bypasses_mfa():
    secret,used,result=enroll(admin,support.ADMIN_TOKEN)
    session={'Authorization':'Bearer '+result['token']}
    assert client.get('/admin/me',headers=admin).status_code==401
    assert client.get('/admin/me',headers=session).json()['role']=='super_admin'
    payload={'mode':'super_admin','token':support.ADMIN_TOKEN}
    assert client.post('/auth/login',json=payload).status_code==401
    assert client.post('/auth/login',json={**payload,'code':used}).status_code==401
    new_code=security.hotp(secret,int(time.time()//30)+1)
    login=client.post('/auth/login',json={**payload,'code':new_code})
    assert login.status_code==200
    assert client.post('/auth/login',json={**payload,'code':new_code}).status_code==401
    assert client.post('/auth/login',json={**payload,'code':result['recovery_codes'][0]}).status_code==200
    # Rate-limit state is intentionally retained within the test; verify replay directly.
    assert not security.verify(support.connect,support.CIPHER,'super-admin',result['recovery_codes'][0])
    with support.connect() as conn:
        row=conn.execute("SELECT secret,recovery FROM mfa_accounts WHERE actor='super-admin'").fetchone()
        assert row['secret']!=secret and result['recovery_codes'][1] not in row['recovery']
    assert client.post('/admin/presence',headers=session,json={'status':'online'}).status_code==200
    assert 'super-admin' in {p['id'] for p in client.get('/support/staff').json()['staff']}
    assert client.post('/admin/logout',headers=session).status_code==200
    assert client.get('/admin/me',headers=session).status_code==401

def test_staff_mfa_session_revocation_recovery_and_admin_reset():
    old=staff('mfa-worker')
    assert client.post('/admin/mfa/setup',headers=old,json={'credential':'wrong'}).status_code==422
    secret,used,result=enroll(old,'presence-test-password')
    current={'Authorization':'Bearer '+result['token']}
    assert client.get('/admin/me',headers=old).status_code==401
    payload={'mode':'staff','staff_id':'mfa-worker','password':'presence-test-password'}
    assert client.post('/auth/login',json=payload).status_code==401
    assert client.post('/auth/login',json={**payload,'code':result['recovery_codes'][0]}).status_code==200
    assert client.post('/auth/login',json={**payload,'code':result['recovery_codes'][0]}).status_code==401
    regenerated=client.post('/admin/mfa/recovery',headers=current,json={'code':result['recovery_codes'][1]})
    assert regenerated.status_code==200
    assert not security.verify(support.connect,support.CIPHER,'mfa-worker',result['recovery_codes'][2])
    assert client.post('/admin/mfa/disable',headers=current,json={'code':regenerated.json()['recovery_codes'][0]}).status_code==200
    assert client.get('/admin/me',headers=current).status_code==401
    login=client.post('/auth/login',json=payload)
    assert login.status_code==200
    new=login.json()['token']
    assert client.post('/admin/staff/mfa-worker/mfa-reset',headers={'Authorization':'Bearer '+new}).status_code==403
    assert client.post('/admin/staff/mfa-worker/mfa-reset',headers=admin).status_code==200
    assert client.get('/admin/me',headers={'Authorization':'Bearer '+new}).status_code==401

def test_mfa_enrollment_expiry_invalid_codes_and_throttling():
    setup=client.post('/admin/mfa/setup',headers=admin,json={'credential':support.ADMIN_TOKEN}).json()
    with support.connect() as conn:
        conn.execute("UPDATE mfa_accounts SET pending_created=? WHERE actor='super-admin'",(time.time()-601,))
    assert client.post('/admin/mfa/confirm',headers=admin,json={'code':security.hotp(setup['secret'],int(time.time()//30))}).status_code==409
    for _ in range(3):
        client.post('/admin/mfa/setup',headers=admin,json={'credential':'wrong'})
    assert client.post('/admin/mfa/setup',headers=admin,json={'credential':support.ADMIN_TOKEN}).status_code==429
