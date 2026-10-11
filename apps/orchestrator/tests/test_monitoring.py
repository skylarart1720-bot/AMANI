import asyncio
import httpx
import pytest
from test_staff_presence import client, admin, staff
import support
import monitoring

@pytest.fixture(autouse=True)
def clean_health(monkeypatch):
    monkeypatch.delenv('AMANI_ALERT_WEBHOOK_URL',raising=False)
    with support.connect() as conn:
        conn.execute('DELETE FROM integration_health');conn.execute('DELETE FROM service_alerts')

def test_deduplicated_incident_recovery_and_private_permissions():
    assert client.get('/admin/monitoring').status_code==401
    assert client.get('/admin/monitoring',headers=staff('health-test')).status_code==403
    for _ in range(3):monitoring.observe(support.connect,'scanner','unreachable','Unavailable')
    result=client.get('/admin/monitoring',headers=admin).json()
    assert len(result['alerts'])==1
    alert=result['alerts'][0]
    assert client.post(f"/admin/alerts/{alert['id']}/ack",headers=admin).status_code==200
    monitoring.observe(support.connect,'scanner','healthy','Recovered')
    result=client.get('/admin/monitoring',headers=admin).json()
    assert result['alerts'][0]['resolved'] and result['alerts'][0]['acknowledged']
    monitoring.observe(support.connect,'scanner','not_configured','Missing settings')
    assert len(monitoring.snapshot(support.connect)['alerts'])==1

def test_provider_failure_details_are_safe_and_distinct():
    secret='private-provider-body-and-token'
    for code,state in [('insufficient_quota','credits_required'),('rate_limit_exceeded','rate_limited')]:
        monitoring.observe_ai(support.connect,httpx.Response(429,json={'error':{'code':code,'message':secret}}))
        assert monitoring.snapshot(support.connect)['services'][0]['state']==state
    monitoring.observe_ai(support.connect,httpx.Response(401,text=secret))
    assert secret not in str(monitoring.snapshot(support.connect))
    monitoring.observe_ai(support.connect,httpx.Response(200))
    assert monitoring.snapshot(support.connect)['alerts'][0]['resolved']

def test_webhook_retry_and_sanitized_payload(monkeypatch):
    monkeypatch.setenv('AMANI_ALERT_WEBHOOK_URL','https://alerts.example.test/hook')
    monitoring.observe(support.connect,'scanner','error','Unavailable')
    monitoring.observe(support.connect,'scanner','error','Unavailable')
    captured=[]
    def handler(request):
        captured.append(request.content)
        return httpx.Response(503)
    original=httpx.AsyncClient
    monkeypatch.setattr(monitoring.httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))
    for _ in range(5):
        with support.connect() as conn:conn.execute('UPDATE service_alerts SET next_attempt=0')
        asyncio.run(monitoring.deliver(support.connect))
    alert=monitoring.snapshot(support.connect)['alerts'][0]
    assert alert['delivery']=='failed' and alert['attempts']==5
    assert len(captured)==5 and b'ack_actor' not in captured[0]
    assert not monitoring.valid_webhook('https://[')
    assert not monitoring.valid_webhook('http://alerts.example.test')
    assert not monitoring.valid_webhook('https://user:password@example.test')
