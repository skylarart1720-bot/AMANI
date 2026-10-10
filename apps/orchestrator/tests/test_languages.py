import asyncio
import json
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import main
import support
import languages

client = TestClient(main.app)
admin = {"Authorization": f"Bearer {support.ADMIN_TOKEN}"}

def session():
    token = client.post('/support/sessions').json()['token']
    return {'Authorization': f'Bearer {token}'}

def test_registry_and_offline_catalogues_are_public_without_generation(monkeypatch):
    async def unexpected(*args, **kwargs):
        raise AssertionError('Public catalogue reads must never spend AI credits')
    monkeypatch.setattr(languages, 'provider', unexpected)
    rows = client.get('/support/languages').json()['languages']
    assert len(rows) == 24 and len({r['code'] for r in rows}) == 24
    assert {'ak', 'ee', 'gaa', 'ha', 'ar', 'zh-CN'} <= {r['code'] for r in rows}
    for row in rows:
        response = client.get(f"/support/languages/{row['code']}")
        assert response.status_code == 200
        assert response.json()['translated'] <= response.json()['total']
    assert client.get('/support/languages/fr').json()['status'] == 'complete'
    assert client.get('/support/languages/../../private').status_code in (401, 404)
    assert client.get('/support/languages/not-a-language').status_code == 404

@pytest.mark.parametrize('code,phrase', [('ak','mmoa'),('ha','hanyoyin'),('sw','viungo'),('ar','الدعم'),('es','enlaces'),('zh-CN','链接')])
def test_offline_chat_respects_selected_language(code, phrase):
    headers = session()
    response = client.post('/support/chat', headers=headers, json={'message':'I need support', 'topic':'mental-health', 'language':code})
    assert response.status_code == 200
    assert phrase in response.json()['reply']
    assert response.json()['mode'] == 'directory'
    client.delete('/support/sessions', headers=headers)

@pytest.mark.parametrize('code,message,expected', [('ak','mepɛ sɛ mewu','frɛ 112'),('ha','ina so in kashe kaina','kira 112'),('ar','أريد أن أموت','112'),('es','quiero suicidarme','112'),('zh-CN','我想自杀','112')])
def test_multilingual_urgent_messages_keep_emergency_number(code, message, expected):
    headers = session()
    response = client.post('/support/chat', headers=headers, json={'message':message,'language':code})
    assert response.json()['triage'] == 'urgent'
    assert expected in response.json()['reply']
    assert response.json()['case_id']
    client.delete('/support/sessions', headers=headers)

def test_unsupported_language_is_rejected():
    headers = session()
    assert client.post('/support/chat', headers=headers, json={'message':'hello','language':'made-up'}).status_code == 422
    client.delete('/support/sessions', headers=headers)

def test_translation_needs_consent_and_message_ownership(monkeypatch):
    owner, stranger = session(), session()
    client.post('/support/chat', headers=owner, json={'message':'I need support'})
    original = client.get('/support/messages', headers=owner).json()['messages'][-1]
    calls = []
    async def translate(content, code):
        calls.append((content, code))
        return 'Respuesta traducida'
    monkeypatch.setattr(languages, 'translate_message', translate)
    body = {'message_id': original['id'], 'language':'es', 'ai_consent':False}
    assert client.post('/support/translate', headers=owner, json=body).status_code == 422
    body['ai_consent'] = True
    assert client.post('/support/translate', headers=stranger, json=body).status_code == 404
    assert not calls
    result = client.post('/support/translate', headers=owner, json=body)
    assert result.json()['translation'] == 'Respuesta traducida'
    assert calls == [(original['content'], 'es')]
    assert client.get('/support/messages', headers=owner).json()['messages'][-1]['content'] == original['content']
    client.delete('/support/sessions', headers=owner)
    client.delete('/support/sessions', headers=stranger)

def test_catalogue_generation_preserves_numbers_and_persists_only_public_wording(monkeypatch, tmp_path):
    monkeypatch.setattr(languages, 'SOURCE', {'Call 112':'Call 112', 'Hello':'Hello'})
    async def provider(messages, *args):
        assert json.loads(messages[-1]['content']) == {'Call 112':'Call 112', 'Hello':'Hello'}
        return json.dumps({'Call 112':'Llama al 112','Hello':'Hola'})
    monkeypatch.setattr(languages, 'provider', provider)
    result = asyncio.run(languages.complete('es', tmp_path))
    assert result['status'] == 'complete'
    assert languages.catalogue('es', tmp_path)['translations']['Call 112'] == 'Llama al 112'
    assert not languages.valid_translation('Call 112', 'Llama al 911')
    assert not languages.valid_translation('See https://example.com', 'Mira https://fake.com')
    assert not languages.valid_translation('Help with {topic}', 'Ayuda con el tema')
    (tmp_path / 'locales' / f'es-{languages.VERSION}.json').unlink()
    assert languages.catalogue('es', tmp_path)['status'] == 'partial'

def test_generation_is_super_admin_only():
    assert client.post('/admin/languages/es').status_code == 401
    client.post('/admin/staff', headers=admin, json={'staff_id':'language-test', 'password':'StrongPass123!'} )
    token = client.post('/auth/login', json={'mode':'staff','staff_id':'language-test','password':'StrongPass123!'}).json()['token']
    assert client.post('/admin/languages/es', headers={'Authorization':f'Bearer {token}'}).status_code == 403

def test_generation_rejects_english_echoes(monkeypatch, tmp_path):
    sentence = 'Please contact the official support service.'
    monkeypatch.setattr(languages, 'SOURCE', {sentence:sentence})
    async def echo(messages, *args):
        return json.dumps({sentence:sentence})
    monkeypatch.setattr(languages, 'provider', echo)
    result = asyncio.run(languages.complete('gaa', tmp_path))
    assert result['status'] == 'unavailable'
    assert result['translated'] == 0
    assert not list(tmp_path.glob('locales/*.json'))

def test_expanded_directory_does_not_claim_confirmed_contact_details():
    records = client.get('/support/directory').json()['referrals']
    additional = [r for r in records if r['id'] in {'legal-aid-commission','access-now-helpline','unhcr-help','rsf-assistance','chraj-complaints'}]
    assert len(additional) == 5
    assert all(r['website'].startswith('https://') and r['verification'] == 'unverified' for r in additional)
