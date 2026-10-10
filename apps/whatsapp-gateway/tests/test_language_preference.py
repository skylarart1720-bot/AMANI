import asyncio
import hashlib
import hmac
import importlib.util
import json
from pathlib import Path
from unittest.mock import AsyncMock
from cryptography.fernet import Fernet
import httpx

def test_whatsapp_language_selection_persists_and_reaches_chat(monkeypatch, tmp_path):
    monkeypatch.setenv('AMANI_DATA_DIR', str(tmp_path))
    monkeypatch.setenv('CHAT_ENCRYPTION_KEY', Fernet.generate_key().decode())
    spec = importlib.util.spec_from_file_location('language_gateway', Path(__file__).resolve().parents[1] / 'src/main.py')
    gateway = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gateway)
    monkeypatch.setattr(gateway, 'META_APP_SECRET', 'test-secret')
    deliver = AsyncMock()
    monkeypatch.setattr(gateway, 'deliver', deliver)
    calls = []
    class FakeClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, url, **kwargs):
            return httpx.Response(200, json={'languages':[{'code':'en','native':'English'},{'code':'ak','native':'Twi / Akan'},{'code':'zh-CN','native':'简体中文'}]},request=httpx.Request('GET',url))
        async def post(self, url, **kwargs):
            calls.append((url, kwargs))
            body = {'token':'synthetic-session'} if url.endswith('/sessions') else {'reply':'Translated reply','referrals':[]}
            return httpx.Response(200,json=body,request=httpx.Request('POST',url))
    monkeypatch.setattr(gateway.httpx, 'AsyncClient', FakeClient)
    def message(identity, text):
        payload = gateway.cipher().encrypt(json.dumps({'from':'15550009999','text':{'body':text}}).encode()).decode()
        with gateway.connect() as db:
            db.execute('INSERT INTO inbox(id,payload,available,created) VALUES(?,?,0,0)', (identity,payload))
            row = dict(db.execute('SELECT * FROM inbox WHERE id=?',(identity,)).fetchone())
        asyncio.run(gateway.process(row))
    message('choose','language ak')
    sender = hmac.new(b'test-secret',b'15550009999',hashlib.sha256).hexdigest()
    with gateway.connect() as db:
        assert db.execute('SELECT language,consent FROM senders WHERE id=?',(sender,)).fetchone()['language'] == 'ak'
    message('chat','I need support')
    body = calls[-1][1]['json']
    assert body['language'] == 'ak' and body['ai_consent'] is False
    message('unknown','language made-up')
    message('chinese','language zh-cn')
    with gateway.connect() as db:
        assert db.execute('SELECT language FROM senders WHERE id=?',(sender,)).fetchone()['language'] == 'zh-CN'
    assert deliver.await_count == 4
