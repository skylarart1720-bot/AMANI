"""Regression check for localhost/127.0.0.1 and cross-site mutation rejection."""
import json
from pathlib import Path
from urllib.parse import urlsplit
import httpx

ROOT = Path(__file__).resolve().parents[1]
services = {item['name']: item['url'] for item in json.loads((ROOT / '.runtime/services.json').read_text())}
for host in ('127.0.0.1', 'localhost'):
    url = f"http://{host}:{urlsplit(services['web']).port}"
    with httpx.Client(timeout=40, trust_env=False) as client:
        response = client.post(url + '/api/support/sessions', headers={'Origin': url})
        assert response.status_code == 200, (host, response.status_code)
        token = response.json()['token']
        response = client.delete(url + '/api/support/sessions', headers={'Origin': url, 'Authorization': 'Bearer ' + token})
        assert response.status_code == 200
        response = client.post(url + '/api/support/sessions', headers={'Origin': 'https://unrelated.example'})
        assert response.status_code == 403
        response = client.post(url + '/api/support/check-link', headers={'Origin': url}, json={'url': 'https://example.com', 'consent': True})
        assert response.status_code == 200, (host, response.status_code)
    print(host + ': session creation, deletion, link check PASS; cross-site request rejected')

with httpx.Client(timeout=40, trust_env=False) as client:
    response = client.post(services['moderator'] + '/api/login', headers={'Origin': 'https://unrelated.example'}, json={'token': 'untrusted-token-with-enough-characters'})
    assert response.status_code == 403
print('Moderator cross-site sign-in: rejected')
