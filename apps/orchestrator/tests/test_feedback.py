from test_staff_presence import client, admin, staff, visitor
import support

def test_feedback_ownership_consent_privacy_and_deletion():
    v=visitor();other=visitor();person=staff('feedback-person')
    case=client.post('/support/handoff',headers=v,json={}).json()['id']
    path=f'/support/cases/{case}/feedback'
    payload={'rating':4,'comment':'Private feedback words','consent':True}
    assert client.post(path,headers=v,json=payload).status_code==409
    client.patch(f'/admin/queue/{case}',headers=admin,json={'status':'resolved'})
    assert client.post(path,headers=other,json=payload).status_code==404
    assert client.post(path,headers=v,json={**payload,'consent':False}).status_code==422
    assert client.post(path,headers=v,json={**payload,'rating':6}).status_code==422
    assert client.post(path,headers=v,json=payload).status_code==200
    assert client.post(path,headers=v,json=payload).status_code==409
    history=client.get('/support/messages',headers=v).json()
    assert history['case']['feedback_submitted']
    assert history['case']['events'][-1]['kind']=='resolved'
    assert 'Private feedback words' not in str(history)
    assert client.get('/admin/feedback',headers=person).status_code==403
    entries=client.get('/admin/feedback',headers=admin).json()['entries']
    assert any(e['comment']=='Private feedback words' for e in entries)
    with support.connect() as conn:
        assert conn.execute('SELECT comment FROM case_feedback WHERE case_id=?',(case,)).fetchone()[0]!='Private feedback words'
    client.delete('/support/sessions',headers=v)
    with support.connect() as conn:
        assert conn.execute('SELECT COUNT(*) FROM case_feedback WHERE case_id=?',(case,)).fetchone()[0]==0
        assert conn.execute('SELECT COUNT(*) FROM case_events WHERE case_id=?',(case,)).fetchone()[0]==0

def test_support_information_is_admin_only_and_publicly_readable():
    person=staff('settings-person')
    payload={'hours':'Monday to Friday, 09:00–17:00 GMT','response':'We aim to respond during staffed hours. No guarantee.'}
    assert client.put('/admin/service-settings',headers=person,json=payload).status_code==403
    previous=client.get('/support/service-settings').json()
    try:
        assert client.put('/admin/service-settings',headers=admin,json=payload).status_code==200
        assert client.get('/support/service-settings').json()==payload
        assert client.put('/admin/service-settings',headers=admin,json={'hours':'   ','response':'   '}).status_code==422
    finally:
        client.put('/admin/service-settings',headers=admin,json=previous)
