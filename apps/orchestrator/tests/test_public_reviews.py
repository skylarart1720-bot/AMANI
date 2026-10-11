from test_staff_presence import client,admin,staff,visitor

def feedback(public):
    v=visitor();case=client.post('/support/handoff',headers=v,json={}).json()['id']
    client.patch(f'/admin/queue/{case}',headers=admin,json={'status':'resolved'})
    assert client.post(f'/support/cases/{case}/feedback',headers=v,json={'rating':2,'comment':'Private name. Helpful support, but the wait was long.','consent':True,'public_consent':public}).status_code==200
    return v,case

def test_only_admin_can_publish_consented_reviews_without_private_identifiers():
    person=staff('reviews-staff');v,case=feedback(True);path=f'/admin/feedback/{case}'
    initial=client.get('/support/reviews').json()['total']
    payload={'published':True,'comment':'Helpful support, but the wait was long.'}
    assert client.patch(path,headers=person,json=payload).status_code==403
    assert client.patch(path,headers=admin,json={**payload,'comment':'Excellent five-star support!'}).status_code==422
    assert client.patch(path,headers=admin,json=payload).status_code==200
    data=client.get('/support/reviews').json()
    assert data['total']==initial+1
    row=next(r for r in data['reviews'] if r['comment']==payload['comment'])
    assert row['rating']==2
    assert set(row)=={'rating','comment','published_at'}
    assert 'Private name' not in str(data) and case not in str(data)
    original=next(e for e in client.get('/admin/feedback',headers=admin).json()['entries'] if e['case_id']==case)
    assert original['comment'].startswith('Private name.')
    assert client.patch(path,headers=admin,json={'published':False}).status_code==200
    assert client.get('/support/reviews').json()['total']==initial
    client.patch(path,headers=admin,json=payload)
    client.delete('/support/sessions',headers=v)
    assert client.get('/support/reviews').json()['total']==initial

def test_private_feedback_cannot_be_published():
    v,case=feedback(False)
    assert client.patch(f'/admin/feedback/{case}',headers=admin,json={'published':True,'comment':''}).status_code==409
    client.delete('/support/sessions',headers=v)
