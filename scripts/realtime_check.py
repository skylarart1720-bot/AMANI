"""Verify live SSE delivery through both frontend proxies, without polling."""
import json
import os
import time
from pathlib import Path
import httpx

ROOT = Path(__file__).resolve().parents[1]
services = {item['name']: item['url'] for item in json.loads((ROOT / '.runtime/services.json').read_text())}
admin_token = os.getenv('ADMIN_API_TOKEN') or (ROOT / 'data/.admin-token').read_text().strip()
with httpx.Client(timeout=40, trust_env=False) as visitor, httpx.Client(timeout=40, trust_env=False) as moderator:
    visitor.headers['Origin'] = services['web']
    moderator.headers['Origin'] = services['moderator']
    login = moderator.post(services['moderator'] + '/api/login', json={'token': admin_token})
    assert login.status_code == 200
    token = visitor.post(services['web'] + '/api/support/sessions').json()['token']
    visitor.headers['Authorization'] = 'Bearer ' + token
    try:
        with moderator.stream('GET', services['moderator'] + '/api/admin/events') as queue_stream:
            assert queue_stream.status_code == 200
            assert 'text/event-stream' in queue_stream.headers['content-type']
            queued = visitor.post(services['web'] + '/api/support/handoff').json()
            case_id = queued['id']
            for line in queue_stream.iter_lines():
                if line.startswith('data: ') and any(item['id'] == case_id for item in json.loads(line[6:])):
                    break
        with visitor.stream('GET', services['web'] + '/api/support/events') as chat_stream:
            assert chat_stream.status_code == 200
            assert 'text/event-stream' in chat_stream.headers['content-type']
            started = time.monotonic()
            response = moderator.post(services['moderator'] + f'/api/admin/queue/{case_id}/reply', json={'message': 'SSE verification reply'})
            assert response.status_code == 200
            for line in chat_stream.iter_lines():
                if line.startswith('data: ') and any(item['content'] == 'SSE verification reply' for item in json.loads(line[6:])['messages']):
                    print(f'PASS: queue and reply delivered over SSE, no polling; reply received in {time.monotonic() - started:.2f}s')
                    break
    finally:
        visitor.delete(services['web'] + '/api/support/sessions')
        moderator.post(services['moderator'] + '/api/logout')
