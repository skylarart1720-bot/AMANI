import hashlib
import hmac
import importlib.util
import json
from pathlib import Path
from fastapi.testclient import TestClient

spec = importlib.util.spec_from_file_location('secure_gateway', Path(__file__).resolve().parents[1] / 'src/main.py')
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)
client = TestClient(gateway.app)

def test_unconfigured_gateway_does_not_claim_delivery(monkeypatch):
    monkeypatch.setattr(gateway, 'configured', lambda: False)
    assert client.get('/health').json()['configured'] is False
    assert client.post('/webhook', json={}).status_code == 503
    assert client.post('/send-message', json={}).status_code == 404

def test_signature_validation_and_duplicate_delivery(monkeypatch):
    monkeypatch.setattr(gateway, 'configured', lambda: True)
    monkeypatch.setattr(gateway, 'META_APP_SECRET', 'test-secret')
    monkeypatch.setattr(gateway, 'META_WHATSAPP_PHONE_NUMBER_ID', 'test-phone')
    body = {'object': 'whatsapp_business_account', 'entry': [{'changes': [{'value': {
        'metadata': {'phone_number_id': 'test-phone'},
        'messages': [{'id': 'security-test-unique-message', 'from': '15550000000', 'type': 'text', 'text': {'body': 'Hello'}}]
    }}]}]}
    raw = json.dumps(body).encode()
    assert client.post('/webhook', content=raw).status_code == 401
    signature = 'sha256=' + hmac.new(b'test-secret', raw, hashlib.sha256).hexdigest()
    for _ in range(2):
        assert client.post('/webhook', content=raw, headers={'x-hub-signature-256': signature}).status_code == 200
    digest = hashlib.sha256(b'security-test-unique-message').hexdigest()
    with gateway.connect() as db:
        rows = db.execute('SELECT payload FROM inbox WHERE id=?', (digest,)).fetchall()
        assert len(rows) == 1
        assert '15550000000' not in rows[0]['payload']

def test_webhook_verification(monkeypatch):
    monkeypatch.setattr(gateway, 'META_WEBHOOK_VERIFY_TOKEN', 'secret-verify-token')
    assert client.get('/webhook', params={'hub.mode': 'subscribe', 'hub.verify_token': 'wrong', 'hub.challenge': '123'}).status_code == 403
    response = client.get('/webhook', params={'hub.mode': 'subscribe', 'hub.verify_token': 'secret-verify-token', 'hub.challenge': '123'})
    assert response.status_code == 200
    assert response.text == '123'
