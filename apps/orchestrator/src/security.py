"""Authenticator MFA with encrypted secrets and single-use recovery codes."""
import base64
import hashlib
import hmac
import json
import secrets
import time
import threading
from urllib.parse import quote
from fastapi import HTTPException, Request
from pydantic import BaseModel, Field

def initialize(connect):
    with connect() as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS mfa_accounts(actor TEXT PRIMARY KEY,secret TEXT NOT NULL DEFAULT '',pending TEXT NOT NULL DEFAULT '',pending_created REAL NOT NULL DEFAULT 0,enabled INTEGER NOT NULL DEFAULT 0,last_step INTEGER NOT NULL DEFAULT -1,recovery TEXT NOT NULL DEFAULT '[]');
        CREATE TABLE IF NOT EXISTS admin_sessions(token_hash TEXT PRIMARY KEY,expires REAL NOT NULL,credential_hash TEXT NOT NULL);
        ''')

def enabled(connect,actor):
    with connect() as conn:
        row=conn.execute('SELECT enabled FROM mfa_accounts WHERE actor=?',(actor,)).fetchone()
    return bool(row and row['enabled'])

def hotp(secret,counter,digits=6):
    key=base64.b32decode(secret+'='*((8-len(secret)%8)%8),casefold=True)
    digest=hmac.new(key,counter.to_bytes(8,'big'),hashlib.sha1).digest()
    offset=digest[-1]&15
    number=int.from_bytes(digest[offset:offset+4],'big')&0x7fffffff
    return str(number%(10**digits)).zfill(digits)

def matching_step(secret,code,now=None):
    code=code.strip()
    if len(code)!=6 or not code.isascii() or not code.isdigit():
        return None
    step=int((time.time() if now is None else now)//30)
    for candidate in (step,step-1,step+1):
        if candidate>=0 and hmac.compare_digest(hotp(secret,candidate),code):
            return candidate
    return None

def recovery_hash(code):
    return hashlib.sha256(code.strip().lower().replace('-','').encode()).hexdigest()

def verify(connect,cipher,actor,code):
    with connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=conn.execute('SELECT * FROM mfa_accounts WHERE actor=? AND enabled=1',(actor,)).fetchone()
        if not row:
            return False
        step=matching_step(cipher.decrypt(row['secret'].encode()).decode(),code)
        if step is not None and step>row['last_step']:
            return bool(conn.execute('UPDATE mfa_accounts SET last_step=? WHERE actor=? AND last_step<?',(step,actor,step)).rowcount)
        digest=recovery_hash(code)
        codes=json.loads(row['recovery'])
        match=next((value for value in codes if hmac.compare_digest(value,digest)),None)
        if match:
            codes.remove(match)
            conn.execute('UPDATE mfa_accounts SET recovery=? WHERE actor=?',(json.dumps(codes),actor))
            return True
    return False

class CodeInput(BaseModel):
    code:str=Field(min_length=1,max_length=128)

class CredentialInput(BaseModel):
    credential:str=Field(min_length=1,max_length=200)

def install(app,connect,cipher,record_audit,replace_session,validate_primary):
    attempts={}
    attempts_lock=threading.Lock()
    app.state.mfa_attempts=attempts
    def throttle(actor):
        now=time.monotonic()
        # Bound authenticated enrollment/disable attempts as well as login attempts.
        with attempts_lock:
            attempts[actor]=[x for x in attempts.get(actor,[]) if x>now-60]
            if len(attempts[actor])>=5:
                raise HTTPException(429,'Too many verification attempts. Please wait a minute.')
            attempts[actor].append(now)
            if len(attempts)>10000:
                for key in list(attempts):
                    if not attempts[key] or attempts[key][-1]<now-60:
                        del attempts[key]

    @app.get('/admin/mfa')
    def status(request:Request):
        with connect() as conn:
            row=conn.execute('SELECT enabled,recovery FROM mfa_accounts WHERE actor=?',(request.state.actor,)).fetchone()
        return {'enabled':bool(row and row['enabled']),'recovery_remaining':len(json.loads(row['recovery'])) if row else 0}

    @app.post('/admin/mfa/setup')
    def setup(request:Request,payload:CredentialInput):
        actor=request.state.actor
        throttle(actor)
        if not validate_primary(actor,payload.credential):
            raise HTTPException(422,'Your current sign-in credential did not match.')
        secret=base64.b32encode(secrets.token_bytes(20)).decode().rstrip('=')
        with connect() as conn:
            if conn.execute('SELECT 1 FROM mfa_accounts WHERE actor=? AND enabled=1',(actor,)).fetchone():
                raise HTTPException(409,'MFA is already enabled.')
            conn.execute("INSERT INTO mfa_accounts(actor,pending,pending_created) VALUES(?,?,?) ON CONFLICT(actor) DO UPDATE SET pending=excluded.pending,pending_created=excluded.pending_created",(actor,cipher.encrypt(secret.encode()).decode(),time.time()))
            record_audit('mfa.enrollment_started',actor,actor,conn=conn)
        return {'secret':secret,'uri':f'otpauth://totp/{quote("AMANI:"+actor)}?secret={secret}&issuer=AMANI&algorithm=SHA1&digits=6&period=30','expires_in':600}

    @app.post('/admin/mfa/confirm')
    def confirm(request:Request,payload:CodeInput):
        actor=request.state.actor
        throttle(actor)
        codes=['-'.join([value[i:i+6] for i in range(0,24,6)]) for value in [secrets.token_hex(12) for _ in range(8)]]
        with connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            row=conn.execute('SELECT * FROM mfa_accounts WHERE actor=?',(actor,)).fetchone()
            if not row or row['enabled'] or not row['pending'] or row['pending_created']<time.time()-600:
                raise HTTPException(409,'Start a new MFA enrollment.')
            step=matching_step(cipher.decrypt(row['pending'].encode()).decode(),payload.code)
            if step is None:
                raise HTTPException(422,'Invalid verification code. Check your authenticator time.')
            conn.execute("UPDATE mfa_accounts SET secret=pending,pending='',pending_created=0,enabled=1,last_step=?,recovery=? WHERE actor=?",(step,json.dumps([recovery_hash(c) for c in codes]),actor))
            record_audit('mfa.enabled',actor,actor,conn=conn)
        identity=replace_session(actor)
        return {**identity,'enabled':True,'recovery_codes':codes}

    @app.post('/admin/mfa/disable')
    def disable(request:Request,payload:CodeInput):
        actor=request.state.actor
        throttle(actor)
        if not verify(connect,cipher,actor,payload.code):
            record_audit('mfa.verification_failed',actor,actor,'denied')
            raise HTTPException(422,'Invalid or already used verification code.')
        with connect() as conn:
            conn.execute('DELETE FROM mfa_accounts WHERE actor=?',(actor,))
            record_audit('mfa.disabled',actor,actor,conn=conn)
        return {**replace_session(actor),'enabled':False}

    @app.post('/admin/mfa/recovery')
    def regenerate_recovery(request:Request,payload:CodeInput):
        actor=request.state.actor
        throttle(actor)
        if not verify(connect,cipher,actor,payload.code):
            raise HTTPException(422,'Invalid or already used verification code.')
        codes=[secrets.token_hex(12) for _ in range(8)]
        with connect() as conn:
            conn.execute('UPDATE mfa_accounts SET recovery=? WHERE actor=?',(json.dumps([recovery_hash(c) for c in codes]),actor))
            record_audit('mfa.recovery_codes_regenerated',actor,actor,conn=conn)
        return {'recovery_codes':codes}

    @app.post('/admin/staff/{staff_id}/mfa-reset')
    def reset_staff(staff_id:str,request:Request):
        with connect() as conn:
            if not conn.execute('SELECT 1 FROM staff_accounts WHERE id=?',(staff_id,)).fetchone():
                raise HTTPException(404,'Staff account not found.')
            conn.execute('DELETE FROM mfa_accounts WHERE actor=?',(staff_id,))
            conn.execute('DELETE FROM staff_sessions WHERE staff_id=?',(staff_id,))
            conn.execute('DELETE FROM staff_presence WHERE actor=?',(staff_id,))
            record_audit('mfa.reset_by_admin',request.state.actor,staff_id,conn=conn)
        return {'reset':True}

def reset_super_admin_mfa(data_dir):
    """Host-only recovery: requires filesystem access, never a public token bypass."""
    import sqlite3
    from contextlib import closing
    from pathlib import Path
    database=Path(data_dir).resolve()/'support.db'
    with closing(sqlite3.connect(database.as_uri()+'?mode=rw',uri=True)) as conn:
        with conn:
            conn.execute('DELETE FROM mfa_accounts WHERE actor=?',('super-admin',))
            conn.execute('DELETE FROM admin_sessions')
            conn.execute('DELETE FROM staff_presence WHERE actor=?',('super-admin',))
            conn.execute('INSERT INTO audit(action,actor,resource,outcome,detail,created) VALUES(?,?,?,?,?,?)',('mfa.host_recovery','host-operator','super-admin','success','Host filesystem recovery',time.time()))

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description='Host-only Super Admin MFA recovery')
    parser.add_argument('action',choices=['reset-super-admin-mfa'])
    parser.add_argument('--data-dir',required=True)
    parser.add_argument('--confirm',action='store_true',required=True)
    args=parser.parse_args()
    reset_super_admin_mfa(args.data_dir)
    print('Super Admin MFA reset; sessions revoked. Sign in and enroll again.')
