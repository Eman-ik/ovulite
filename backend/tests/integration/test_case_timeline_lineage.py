"""The case timeline shows the full lineage: OPU, then IVM, then IVF, then transfer.

Built through the API, the same way a user would record it, so the timeline is
checked against what was actually persisted rather than against the database.
"""

import pytest


def _post(client, headers, url, body, expected=201):
    r = client.post(url, headers=headers, json=body)
    assert r.status_code == expected, f"{url}: {r.status_code} {r.text}"
    return r.json()


@pytest.fixture
def lab_headers(client, db_session, admin_user):
    """An embryologist in the admin's organization."""
    from app.auth.security import hash_password
    from app.models.user import User

    admin = db_session.query(User).filter(User.username == "admin").one()
    db_session.add(User(username="timeline_lab", password_hash=hash_password("Str0ng!Passw0rd"),
                        role="embryologist", active=True, organization_id=admin.organization_id))
    db_session.commit()
    r = client.post("/auth/login", data={"username": "timeline_lab", "password": "Str0ng!Passw0rd"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def vet_headers(client, db_session, admin_user):
    """A veterinarian in the admin's organization."""
    from app.auth.security import hash_password
    from app.models.user import User

    admin = db_session.query(User).filter(User.username == "admin").one()
    db_session.add(User(username="timeline_vet", password_hash=hash_password("Str0ng!Passw0rd"),
                        role="veterinarian", active=True, organization_id=admin.organization_id))
    db_session.commit()
    r = client.post("/auth/login", data={"username": "timeline_vet", "password": "Str0ng!Passw0rd"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.integration
def test_case_timeline_shows_opu_ivm_ivf_and_transfer_in_order(client, lab_headers, vet_headers):
    donor = _post(client, lab_headers, "/donors/", {"tag_id": "TL-DONOR", "breed": "Holstein"})
    opu = _post(client, lab_headers, "/opu-sessions/",
                {"donor_id": donor["donor_id"], "opu_date": "2026-01-10"})
    ivm = _post(client, lab_headers, f"/lab/opu-sessions/{opu['opu_id']}/ivm-batches",
                {"ivm_date": "2026-01-11", "oocytes_in": 9, "mature_oocytes_out": 6})
    ivf = _post(client, lab_headers, "/ivf-batches/",
                {"opu_id": opu["opu_id"], "ivm_batch_id": ivm["ivm_batch_id"], "ivf_date": "2026-01-12"})
    embryo = _post(client, lab_headers, "/embryos/", {
        "donor_id": donor["donor_id"], "opu_id": opu["opu_id"], "ivf_batch_id": ivf["ivf_batch_id"],
        "stage": 7, "grade": 1, "fresh_or_frozen": "Fresh",
    })
    recipient = _post(client, vet_headers, "/recipients/",
                      {"tag_id": "TL-RECIP", "farm_location": "Timeline Farm", "cow_or_heifer": "Cow"})
    transfer = _post(client, vet_headers, "/transfers/", {
        "et_date": "2026-01-20", "embryo_id": embryo["embryo_id"],
        "recipient_id": recipient["recipient_id"], "cl_measure_mm": 18.0,
    })

    timeline = client.get(f"/case-timeline/{transfer['transfer_id']}/timeline", headers=vet_headers)
    assert timeline.status_code == 200, timeline.text
    events = timeline.json()["events"]

    kinds = [e["kind"] for e in events]
    assert kinds == ["opu", "ivm", "ivf", "transfer"], events
    by_kind = {e["kind"]: e for e in events}
    assert by_kind["ivm"]["record_id"] == ivm["ivm_batch_id"]
    assert by_kind["ivm"]["label"] == "IVM batch"
    assert by_kind["ivf"]["record_id"] == ivf["ivf_batch_id"]
