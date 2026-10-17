"""An embryo's OPU session and IVF batch must be real, in this organization, and
consistent with each other."""

import uuid
from datetime import date

import pytest

from app.models.donor import Donor
from app.models.opu_session import OPUSession
from app.models.organization import Organization


def _create_opu_session(client, auth_headers, tag_id):
    donor = client.post("/donors/", json={"tag_id": tag_id, "breed": "Holstein"}, headers=auth_headers)
    assert donor.status_code == 201, donor.text
    opu = client.post(
        "/opu-sessions/", json={"donor_id": donor.json()["donor_id"], "opu_date": "2026-01-15"},
        headers=auth_headers,
    )
    assert opu.status_code == 201, opu.text
    return opu.json()["opu_id"]


def _create_ivf_batch(client, auth_headers, opu_id):
    ivm = client.post(
        f"/lab/opu-sessions/{opu_id}/ivm-batches",
        json={"ivm_date": "2026-01-15", "oocytes_in": 9, "mature_oocytes_out": 6},
        headers=auth_headers,
    )
    assert ivm.status_code in (200, 201), ivm.text
    batch = client.post(
        "/ivf-batches/", json={"opu_id": opu_id, "ivm_batch_id": ivm.json()["ivm_batch_id"]},
        headers=auth_headers,
    )
    assert batch.status_code == 201, batch.text
    return batch.json()["ivf_batch_id"]


@pytest.mark.integration
def test_embryo_stores_opu_and_ivf_links(client, auth_headers):
    opu_id = _create_opu_session(client, auth_headers, "EMB-LINK-1")
    ivf_id = _create_ivf_batch(client, auth_headers, opu_id)

    resp = client.post(
        "/embryos/", json={"opu_id": opu_id, "ivf_batch_id": ivf_id, "stage": 7, "grade": 1},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["opu_id"] == opu_id
    assert resp.json()["ivf_batch_id"] == ivf_id


@pytest.mark.integration
def test_ivf_batch_without_opu_takes_its_session(client, auth_headers):
    opu_id = _create_opu_session(client, auth_headers, "EMB-LINK-2")
    ivf_id = _create_ivf_batch(client, auth_headers, opu_id)

    resp = client.post("/embryos/", json={"ivf_batch_id": ivf_id, "stage": 7}, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    assert resp.json()["opu_id"] == opu_id


@pytest.mark.integration
def test_embryo_rejects_ivf_batch_from_another_opu(client, auth_headers):
    opu_a = _create_opu_session(client, auth_headers, "EMB-XOPU-A")
    opu_b = _create_opu_session(client, auth_headers, "EMB-XOPU-B")
    ivf_of_a = _create_ivf_batch(client, auth_headers, opu_a)

    resp = client.post(
        "/embryos/", json={"opu_id": opu_b, "ivf_batch_id": ivf_of_a, "stage": 7}, headers=auth_headers
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.integration
def test_embryo_rejects_unknown_opu_and_ivf_ids(client, auth_headers):
    bad_opu = client.post("/embryos/", json={"opu_id": 999999, "stage": 7}, headers=auth_headers)
    assert bad_opu.status_code == 422, bad_opu.text
    bad_ivf = client.post("/embryos/", json={"ivf_batch_id": 999999, "stage": 7}, headers=auth_headers)
    assert bad_ivf.status_code == 422, bad_ivf.text


@pytest.mark.integration
def test_embryo_rejects_links_to_another_organization(client, db_session, auth_headers):
    suffix = uuid.uuid4().hex[:6]
    other = Organization(name=f"Other Clinic {suffix}", slug=f"other-emb-{suffix}")
    db_session.add(other)
    db_session.flush()
    donor = Donor(tag_id=f"OTHER-{suffix}", breed="Holstein", organization_id=other.organization_id)
    db_session.add(donor)
    db_session.flush()
    foreign_opu = OPUSession(
        donor_id=donor.donor_id, opu_date=date(2026, 1, 15), organization_id=other.organization_id
    )
    db_session.add(foreign_opu)
    db_session.commit()

    resp = client.post(
        "/embryos/", json={"opu_id": foreign_opu.opu_id, "stage": 7}, headers=auth_headers
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.integration
def test_update_can_clear_and_reset_the_links(client, auth_headers):
    opu_a = _create_opu_session(client, auth_headers, "EMB-UPD-A")
    opu_b = _create_opu_session(client, auth_headers, "EMB-UPD-B")
    ivf_a = _create_ivf_batch(client, auth_headers, opu_a)
    embryo_id = client.post(
        "/embryos/", json={"opu_id": opu_a, "ivf_batch_id": ivf_a, "stage": 7}, headers=auth_headers
    ).json()["embryo_id"]

    # Moving the session alone leaves a batch that is no longer from it: refused.
    moved = client.put(f"/embryos/{embryo_id}", json={"opu_id": opu_b}, headers=auth_headers)
    assert moved.status_code == 422, moved.text

    cleared = client.put(
        f"/embryos/{embryo_id}", json={"opu_id": None, "ivf_batch_id": None}, headers=auth_headers
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["opu_id"] is None
    assert cleared.json()["ivf_batch_id"] is None
