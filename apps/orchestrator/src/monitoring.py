"""Private operational health and deduplicated failure/recovery alerts."""
import asyncio
import os
import shutil
import time
from pathlib import Path
from urllib.parse import urlsplit
import httpx
from fastapi import HTTPException, Request

FAILURES={'unreachable','error','credits_required','rate_limited','stale','low_space'}

def valid_webhook(url):
    try:
        parsed=urlsplit(url)
        return parsed.scheme=='https' and bool(parsed.hostname) and not parsed.username and not parsed.password
    except ValueError:
        return False
def initialize(connect):
    with connect() as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS integration_health(name TEXT PRIMARY KEY,state TEXT NOT NULL,detail TEXT NOT NULL,checked REAL NOT NULL,failures INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS service_alerts(id INTEGER PRIMARY KEY,service TEXT NOT NULL,state TEXT NOT NULL,detail TEXT NOT NULL,created REAL NOT NULL,resolved REAL,acknowledged REAL,ack_actor TEXT,delivery TEXT NOT NULL DEFAULT 'pending',attempts INTEGER NOT NULL DEFAULT 0,next_attempt REAL NOT NULL DEFAULT 0);
        ''')

def observe(connect,name,state,detail):
    now=time.time()
    with connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        previous=conn.execute('SELECT * FROM integration_health WHERE name=?',(name,)).fetchone()
        failures=(previous['failures']+1 if previous and previous['state'] in FAILURES else 1) if state in FAILURES else 0
        conn.execute('INSERT INTO integration_health VALUES(?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET state=excluded.state,detail=excluded.detail,checked=excluded.checked,failures=excluded.failures',(name,state,detail,now,failures))
        incident=conn.execute('SELECT id FROM service_alerts WHERE service=? AND resolved IS NULL',(name,)).fetchone()
        if state in FAILURES and failures>=2 and not incident:
            conn.execute('INSERT INTO service_alerts(service,state,detail,created) VALUES(?,?,?,?)',(name,state,detail,now))
        elif incident and state in FAILURES:
            conn.execute('UPDATE service_alerts SET state=?,detail=? WHERE id=?',(state,detail,incident['id']))
        elif incident and state=='healthy':
            conn.execute("UPDATE service_alerts SET resolved=?,delivery='pending',attempts=0,next_attempt=0 WHERE id=?",(now,incident['id']))
        # Limit historical metadata; do not delete active incidents.
        conn.execute('DELETE FROM service_alerts WHERE resolved IS NOT NULL AND resolved<?',(now-90*86400,))

def observe_ai(connect,response=None,error=None):
    if error is not None:
        observe(connect,'AI replies','unreachable','Provider request failed. Check connectivity and provider availability.')
        return
    status=response.status_code
    if 200<=status<300:
        observe(connect,'AI replies','healthy','The latest consented AI request succeeded.')
    elif status==429:
        code=''
        try:
            body=response.json();value=body.get('error',{})
            code=str(value.get('code','') if isinstance(value,dict) else '')
        except (ValueError,AttributeError):
            pass
        credit=code in {'insufficient_quota','credit_balance_exhausted','billing_hard_limit_reached'}
        observe(connect,'AI replies','credits_required' if credit else 'rate_limited','Provider credit or quota is exhausted. Fund the account.' if credit else 'Provider rate limit reached. Retry later or review provider limits.')
    elif status in (401,403):
        observe(connect,'AI replies','error','Provider rejected authentication or permissions. Check the key and model access.')
    else:
        observe(connect,'AI replies','error','Provider returned an unsuccessful response. Check provider availability and model settings.')

async def probe(connect,name,url):
    if not url:
        observe(connect,name,'not_configured','Service address has not been configured.')
        return
    try:
        async with httpx.AsyncClient(timeout=3,trust_env=False) as client:
            response=await client.get(url.rstrip('/')+'/health')
        if not response.is_success:
            observe(connect,name,'error','Health endpoint returned an unsuccessful response.')
        elif isinstance(response.json(),dict) and response.json().get('configured',False):
            observe(connect,name,'healthy','Health endpoint is reachable and reports configured. End-to-end delivery still needs verification.')
        else:
            observe(connect,name,'not_configured','Service is reachable but its provider settings are incomplete.')
    except (httpx.HTTPError,ValueError):
        observe(connect,name,'unreachable','Health endpoint could not be reached or returned invalid data.')

async def deliver(connect):
    url=os.getenv('AMANI_ALERT_WEBHOOK_URL','')
    if not valid_webhook(url):
        return
    with connect() as conn:
        rows=conn.execute("SELECT * FROM service_alerts WHERE delivery='pending' AND attempts<5 AND next_attempt<=? ORDER BY id LIMIT 5",(time.time(),)).fetchall()
    async def send(row):
        payload={key:row[key] for key in ('id','service','state','detail','created','resolved')}
        headers={}
        if os.getenv('AMANI_ALERT_WEBHOOK_TOKEN'):
            headers['Authorization']='Bearer '+os.environ['AMANI_ALERT_WEBHOOK_TOKEN']
        try:
            async with httpx.AsyncClient(timeout=3,trust_env=False) as client:
                response=await client.post(url,json=payload,headers=headers)
            success=response.is_success
        except httpx.HTTPError:
            success=False
        with connect() as conn:
            conn.execute('UPDATE service_alerts SET delivery=?,attempts=attempts+1,next_attempt=? WHERE id=? AND resolved IS ?',('sent' if success else 'failed' if row['attempts']>=4 else 'pending',time.time()+60*(2**row['attempts']),row['id'],row['resolved']))
    await asyncio.gather(*(send(row) for row in rows))

async def check(connect,data):
    await asyncio.gather(probe(connect,'Link scanner',os.getenv('URL_SAFETY_URL')),probe(connect,'WhatsApp gateway',os.getenv('WHATSAPP_GATEWAY_URL')))
    if not (os.getenv('OPENAI_API_KEY') or os.getenv('LLM_API_KEY')):
        observe(connect,'AI replies','not_configured','AI provider credentials are missing.')
    else:
        with connect() as conn:
            previous=conn.execute("SELECT 1 FROM integration_health WHERE name='AI replies'").fetchone()
        if not previous:
            observe(connect,'AI replies','not_verified','Configured; health will be updated by real consented AI requests. Monitoring does not spend AI credits.')
        else:
            with connect() as conn:
                conn.execute("UPDATE integration_health SET state='not_verified',detail='Configured; awaiting a consented provider request.' WHERE name='AI replies' AND state='not_configured'")
    free=shutil.disk_usage(data).free//(1024*1024)
    observe(connect,'Data storage','healthy' if free>=128 else 'low_space','Data directory has adequate free space.' if free>=128 else 'Less than 128 MB free. Expand storage before writes fail.')
    directory=os.getenv('AMANI_BACKUP_DIR','')
    if not directory:
        observe(connect,'Backup freshness','not_configured','Set AMANI_BACKUP_DIR to the directory populated by your backup schedule. This check does not create backups.')
    else:
        try:
            files=list(Path(directory).glob('*.amani-backup'))
            latest=max((p.stat().st_mtime for p in files if p.is_file()),default=0)
            observe(connect,'Backup freshness','healthy' if latest>time.time()-86400 else 'stale','An encrypted archive was written within 24 hours; this does not prove recoverability.' if latest>time.time()-86400 else 'No encrypted backup archive written in the last 24 hours. Check the backup schedule and storage.')
        except OSError:
            observe(connect,'Backup freshness','error','Backup directory could not be inspected. Check permissions and storage.')
    await deliver(connect)

def snapshot(connect):
    with connect() as conn:
        services=[dict(r) for r in conn.execute('SELECT * FROM integration_health ORDER BY name')]
        alerts=[dict(r) for r in conn.execute('SELECT * FROM service_alerts ORDER BY id DESC LIMIT 50')]
    webhook=os.getenv('AMANI_ALERT_WEBHOOK_URL','')
    return {'services':services,'alerts':alerts,'alert_delivery':'Configured' if valid_webhook(webhook) else 'Not configured; alerts remain in this dashboard','check_interval_seconds':60}

def install(app,connect,data,record_audit):
    check_lock=asyncio.Lock()
    async def run_check():
        async with check_lock:
            await check(connect,data)
    async def loop():
        while True:
            try:
                await run_check()
            except Exception:
                # Keep the checker alive; never log environment values or provider bodies.
                import logging
                logging.getLogger('amani.monitoring').error('Operational health check failed; inspect storage and configuration.')
            await asyncio.sleep(60)
    @app.on_event('startup')
    async def start():
        app.state.monitoring_task=asyncio.create_task(loop())
    @app.on_event('shutdown')
    async def stop():
        task=getattr(app.state,'monitoring_task',None)
        if task:
            task.cancel()
            try:await task
            except asyncio.CancelledError:pass
    @app.get('/admin/monitoring')
    def overview(request:Request):
        return snapshot(connect)
    @app.post('/admin/monitoring/check')
    async def manual_check(request:Request):
        await run_check()
        record_audit('monitoring.checked',request.state.actor,'monitoring')
        return snapshot(connect)
    @app.post('/admin/alerts/{alert_id}/ack')
    def acknowledge(alert_id:int,request:Request):
        with connect() as conn:
            if not conn.execute('UPDATE service_alerts SET acknowledged=?,ack_actor=? WHERE id=?',(time.time(),request.state.actor,alert_id)).rowcount:
                raise HTTPException(404,'Alert not found')
            record_audit('monitoring.alert_acknowledged',request.state.actor,str(alert_id),conn=conn)
        return {'acknowledged':True}
    @app.post('/admin/alerts/{alert_id}/retry')
    def retry(alert_id:int,request:Request):
        with connect() as conn:
            if not conn.execute("UPDATE service_alerts SET delivery='pending',attempts=0,next_attempt=0 WHERE id=?",(alert_id,)).rowcount:
                raise HTTPException(404,'Alert not found')
            record_audit('monitoring.alert_delivery_retried',request.state.actor,str(alert_id),conn=conn)
        return {'queued':True}
