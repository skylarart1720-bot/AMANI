from test_staff_presence import client, admin, staff, visitor, online_ids
import support

def test_busy_staff_cannot_receive_new_selected_requests():
    headers = staff('busy-management')
    client.post('/admin/presence',headers=headers,json={'status':'online'})
    assert 'busy-management' in online_ids()
    assert client.post('/admin/presence',headers=headers,json={'status':'busy'}).json()['status']=='busy'
    assert 'busy-management' not in online_ids()
    assert client.post('/support/handoff',headers=visitor(),json={'staff_id':'busy-management'}).status_code==409
    assert client.get('/admin/activity',headers=headers).json()['staff'][0]['status']=='busy'

def test_notes_transfers_and_activity_respect_case_access():
    first, second = staff('case-first'), staff('case-second')
    v = visitor()
    case = client.post('/support/handoff',headers=v,json={}).json()['id']
    assert client.post(f'/admin/queue/{case}/transfer',headers=admin,json={'staff_id':'case-first'}).status_code==200
    assert client.post(f'/admin/queue/{case}/notes',headers=first,json={'content':'Private handover details'}).status_code==200
    assert client.get(f'/admin/queue/{case}/notes',headers=second).status_code==403
    assert client.post(f'/admin/queue/{case}/transfer',headers=second,json={'staff_id':None}).status_code==403
    assert 'Private handover details' not in client.get('/support/messages',headers=v).text
    with support.connect() as conn:
        assert conn.execute('SELECT content FROM case_notes WHERE case_id=?',(case,)).fetchone()['content']!='Private handover details'
    assert client.post(f'/admin/queue/{case}/transfer',headers=first,json={'staff_id':'missing-person'}).status_code==422
    assert client.post(f'/admin/queue/{case}/transfer',headers=first,json={'staff_id':'case-second'}).status_code==200
    assert client.get(f'/admin/queue/{case}/notes',headers=first).status_code==403
    assert client.get(f'/admin/queue/{case}/notes',headers=second).json()['notes'][0]['content']=='Private handover details'
    client.post(f'/admin/queue/{case}/reply',headers=second,json={'message':'A support reply'})
    client.patch(f'/admin/queue/{case}',headers=second,json={'status':'resolved'})
    activity=client.get('/admin/activity',headers=second).json()['staff']
    assert len(activity)==1 and activity[0]['id']=='case-second'
    assert activity[0]['resolved']>=1 and activity[0]['replies_30_days']>=1
    assert client.patch(f'/admin/queue/{case}',headers=second,json={'status':'queued'}).status_code==200
    client.delete('/support/sessions',headers=v)
    with support.connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM case_notes WHERE case_id=?',(case,)).fetchone()[0]==0
