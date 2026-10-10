"""Referral records must state how far they have actually been checked, and never imply more."""
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import main
import support

client = TestClient(main.app)
admin = {"Authorization": "Bearer " + support.ADMIN_TOKEN}

def session():
    return {"Authorization": "Bearer " + client.post("/support/sessions").json()["token"]}

def save(**overrides):
    payload = {"id": "probe-contact", "title": "Probe contact", "organisation": "Probe Organisation", "category": "climate",
               "region": "Ghana", "website": "https://example.org/contact", "notes": "A probe record for coverage.",
               "hours": "Confirm with organisation", "languages": ["English"]}
    payload.update(overrides)
    response = client.put("/admin/directory", headers=admin, json=payload)
    assert response.status_code == 200, response.text
    return response.json()

def test_seeded_contacts_report_their_real_check_state():
    referrals = client.get("/support/directory").json()["referrals"]
    by_id = {r["id"]: r for r in referrals}
    assert by_id["emergency"]["verification"] == "verified"
    assert by_id["digital-rights"]["verification"] == "verified"
    assert by_id["climate"]["verification"] == "unverified"
    assert by_id["climate"]["verified_at"] is None
    assert all(r["trust"] == "official" for r in referrals)
    assert all(r["channels"] for r in referrals)

def test_verification_state_is_derived_from_check_dates():
    assert support.verification_state({}) == "unverified"
    assert support.verification_state({"verified_at": "2026-01-01"}) == "verified"
    assert support.verification_state({"verified_at": "2026-01-01", "review_due": "2099-01-01"}) == "verified"
    assert support.verification_state({"verified_at": "2026-01-01", "review_due": "2000-01-01"}) == "stale"
    assert support.verification_state({"review_due": "2000-01-01"}) == "unverified"

def test_stale_contacts_are_labelled_rather_than_shown_as_confirmed():
    saved = save(verified_at="2020-01-01", review_due="2021-01-01", trust="community", evidence="Checked on the public listing page.")
    assert saved["verification"] == "stale"
    assert saved["verified_at"] == "2020-01-01"
    public = {r["id"]: r for r in client.get("/support/directory").json()["referrals"]}
    assert public["probe-contact"]["verification"] == "stale"

def test_unverified_contacts_do_not_claim_a_check():
    saved = save(verified_at=None, trust="unverified")
    assert saved["verification"] == "unverified"
    assert saved["evidence"] is None

def test_records_saved_before_these_fields_are_still_served():
    legacy = {"id": "legacy-contact", "title": "Legacy contact", "organisation": "Legacy Organisation", "category": "activism",
              "region": "Ghana", "phone": None, "website": "https://example.org/legacy", "notes": "Stored before the new fields.",
              "verified_at": None, "hours": "Confirm with organisation", "languages": ["English"]}
    with support.connect() as conn:
        conn.execute("INSERT OR REPLACE INTO directory VALUES(?,?)", (legacy["id"], json.dumps(legacy)))
    served = {r["id"]: r for r in client.get("/support/directory").json()["referrals"]}
    record = served["legacy-contact"]
    assert record["verification"] == "unverified"
    assert record["regions"] == ["Ghana"]
    assert record["channels"] == ["website"]
    assert record["trust"] == "unverified"
    assert record["review_due"] is None

def test_coarse_region_filter_never_requires_a_precise_location():
    ghana = client.get("/support/directory", params={"region": "Ghana"}).json()["referrals"]
    assert ghana and all("Ghana" in r["regions"] for r in ghana)
    international = client.get("/support/directory", params={"region": "international"}).json()["referrals"]
    assert international and all("International" in r["regions"] for r in international)
    assert {r["id"] for r in ghana}.isdisjoint({r["id"] for r in international})
    assert client.get("/support/directory", params={"region": "x" * 80}).status_code == 422

def test_directory_filters_by_topic():
    cyber = client.get("/support/directory", params={"category": "digital-rights"}).json()["referrals"]
    assert cyber and all(r["category"] == "digital-rights" for r in cyber)
    assert {"digital-rights", "access-now-helpline", "rsf-digital", "nca-complaints"} <= {r["id"] for r in cyber}
    assert client.get("/support/directory", params={"category": "not-a-topic"}).json()["referrals"] == []

def test_saving_keeps_region_and_regions_consistent():
    saved = save(regions=["Ghana", "International"])
    assert saved["regions"] == ["Ghana", "International"]
    assert saved["region"] == "Ghana"
    served = {r["id"]: r for r in client.get("/support/directory").json()["referrals"]}
    assert served["probe-contact"]["regions"] == ["Ghana", "International"]
    save(regions=["International"])
    served = {r["id"]: r for r in client.get("/support/directory").json()["referrals"]}
    assert served["probe-contact"]["region"] == "International"
    assert served["probe-contact"]["regions"] == ["International"]

def test_unknown_contact_channels_are_rejected():
    response = client.put("/admin/directory", headers=admin, json={
        "id": "bad-channel", "title": "Bad", "organisation": "Bad", "category": "climate", "region": "Ghana",
        "website": "https://example.org/bad", "notes": "n", "hours": "h", "channels": ["carrier-pigeon"]})
    assert response.status_code == 422

def test_chat_region_prefers_matching_contacts_and_is_never_required():
    headers = session()
    save(region="Ghana", regions=["Ghana"])
    matched = client.post("/support/chat", headers=headers, json={"message": "I want information about climate action", "topic": "climate", "region": "Ghana"})
    assert matched.status_code == 200
    assert all(r["category"] == "climate" for r in matched.json()["referrals"])
    unmatched = client.post("/support/chat", headers=headers, json={"message": "climate pollution in my community", "topic": "climate", "region": "Nowhere-at-all"})
    assert unmatched.status_code == 200
    assert unmatched.json()["referrals"], "an unmatched region must fall back rather than hide every contact"
    assert client.post("/support/chat", headers=headers, json={"message": "climate", "region": "x" * 80}).status_code == 422
    client.delete("/support/sessions", headers=headers)

def test_directory_edits_are_audited_with_the_record_identifier():
    save(id="audited-contact", region="Ghana", regions=["Ghana"])
    response = client.get("/admin/audit", headers=admin, params={"action": "directory.updated"})
    assert response.status_code == 200
    assert any(e["resource"] == "audited-contact" and e["actor"] == "super-admin" for e in response.json()["entries"])
