"""Executable form of the SDS test plan (sections 5.1-5.4).

Every test is named for its plan ID (for example ``test_U2_3_...``) so the
results can be read straight back against the plan. Each asserts the behaviour
the plan expects. Where the system does not yet behave that way the test FAILS,
on purpose: a known gap is recorded as a failure, not hidden with xfail.

Notes on mapping to the plan:
  * ``validateEmail()`` is not a function in this codebase. Email validation is
    done by Pydantic ``EmailStr`` on the user schemas, so those tests exercise
    that path.
  * The plan's usernames ``admin1``, ``emb1`` and ``vet1`` do not exist. Users
    with those names are created with the matching roles for the run.
  * The plan's embryo status "Available" is not a status in this system. The
    closest one, "Transferable", is used.
  * UI-only steps (redirect after login, screens rendering) were checked in the
    browser against the demo database; the plan rows that need a browser are
    marked as such in the results.
"""

from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.auth.security import hash_password
from app.models.embryo import Embryo
from app.models.et_transfer import ETTransfer
from app.models.prediction import Prediction
from app.models.user import User
from app.schemas.et_transfer import ETTransferCreate, ETTransferNew
from app.schemas.user import UserCreate

PW = "Str0ng!Passw0rd"
TODAY = date.today().isoformat()

IMAGE_CANDIDATES = [
    Path(__file__).resolve().parents[3] / "docs" / "Blastocystimages" / "Blastocyst images" / "blq1.jpg",
    Path(r"D:/Ovulite new/docs/Blastocystimages/Blastocyst images/blq1.jpg"),
]


def _image_bytes() -> bytes:
    for p in IMAGE_CANDIDATES:
        if p.exists():
            return p.read_bytes()
    pytest.skip("blastocyst image not available")


# ── helpers ────────────────────────────────────────────────────────────────

def _tag(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:6]}".upper()


def _mkuser(db, role: str, username: str | None = None) -> str:
    admin = db.query(User).filter(User.username == "admin").first()
    username = username or f"sds_{role}_{uuid.uuid4().hex[:6]}"
    db.add(User(username=username, password_hash=hash_password(PW), role=role,
                active=True, organization_id=admin.organization_id))
    db.commit()
    return username


def _h(client, db, role: str, username: str | None = None) -> dict:
    user = _mkuser(db, role, username)
    r = client.post("/auth/login", data={"username": user, "password": PW})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _ok(r, *codes):
    codes = codes or (200, 201)
    assert r.status_code in codes, f"{r.status_code}: {r.text[:300]}"
    return r.json()


def _donor(client, h):
    return _ok(client.post("/donors/", headers=h, json={"tag_id": _tag("DNR")}), 201)


def _sire(client, h):
    return _ok(client.post("/sires/", headers=h, json={"name": _tag("SIRE")}), 201)


def _opu(client, h, donor_id, oocytes=10):
    return _ok(client.post("/opu-sessions/", headers=h, json={
        "donor_id": donor_id, "opu_date": TODAY, "oocytes_recovered": oocytes}), 201)


def _ivm(client, h, opu_id):
    return _ok(client.post(f"/lab/opu-sessions/{opu_id}/ivm-batches", headers=h, json={
        "ivm_date": TODAY, "oocytes_in": 9, "mature_oocytes_out": 6}))


def _ivf(client, h, opu_id, ivm_id=None, sire_id=None):
    body = {"opu_id": opu_id, "ivf_date": TODAY, "oocytes_used": 6, "mature_oocytes": 6}
    if ivm_id is not None:
        body["ivm_batch_id"] = ivm_id
    if sire_id is not None:
        body["sire_id"] = sire_id
    return client.post("/ivf-batches/", headers=h, json=body)


def _embryo(client, h, ivf_id, **extra):
    body = {"ivf_batch_id": ivf_id, "opu_date": TODAY, "stage": 7,
            "fresh_or_frozen": "Fresh", "status": "In Culture"}
    body.update(extra)
    return client.post("/embryos/", headers=h, json=body)


def _recipient(client, h):
    return _ok(client.post("/recipients/", headers=h, json={"tag_id": _tag("RCP")}), 201)


def _et(client, h, embryo_id, recipient_id, cl=18.0, **extra):
    body = {"et_date": TODAY, "embryo_id": embryo_id, "recipient_id": recipient_id, "cl_measure_mm": cl}
    body.update(extra)
    return client.post("/transfers/", headers=h, json=body)


def _pc(client, h, transfer_id, result):
    return client.post(f"/vet/transfers/{transfer_id}/pregnancy-checks", headers=h,
                       json={"check_date": TODAY, "result": result})


def _full_chain(client, h):
    """Donor -> OPU -> IVM -> IVF -> embryo, with a sire. Returns the ids."""
    donor = _donor(client, h)
    sire = _sire(client, h)
    opu = _opu(client, h, donor["donor_id"])
    ivm = _ivm(client, h, opu["opu_id"])
    ivf = _ok(_ivf(client, h, opu["opu_id"], ivm_id=ivm["ivm_batch_id"], sire_id=sire["sire_id"]), 201)
    emb = _ok(_embryo(client, h, ivf["ivf_batch_id"], donor_id=donor["donor_id"],
                      opu_id=opu["opu_id"], sire_id=sire["sire_id"]), 201)
    return {"donor": donor, "sire": sire, "opu": opu, "ivm": ivm, "ivf": ivf, "embryo": emb}


# ══════════════════════════════════════════════════════════════════════════
# 5.1 Unit testing
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.acceptance
def test_U1_1_valid_email_accepted():
    """Plan U1-1: abc@gmail.com -> True (checked via the user schema)."""
    assert UserCreate(username="abc", password=PW, email="abc@gmail.com").email == "abc@gmail.com"


@pytest.mark.acceptance
def test_U1_2_email_without_at_sign_rejected():
    """Plan U1-2: abc.gmail.com -> False."""
    with pytest.raises(ValidationError):
        UserCreate(username="abc", password=PW, email="abc.gmail.com")


@pytest.mark.acceptance
def test_U1_3_empty_email_rejected():
    """Plan U1-3: "" -> False."""
    with pytest.raises(ValidationError):
        UserCreate(username="abc", password=PW, email="")


@pytest.mark.acceptance
def test_U2_1_complete_et_record_validates():
    """Plan U2-1: all required ET values supplied -> valid."""
    ETTransferCreate(et_date=date.today(), cl_measure_mm=18, recipient_id=1, embryo_id=1)


@pytest.mark.acceptance
def test_U2_2_missing_cl_measure_rejected():
    """Plan U2-2: CL Measure = NULL -> the record is rejected.

    A new ET record must name a CL measure. The edit route still validates
    through ETTransferCreate, so older rows without one stay editable.

    """
    with pytest.raises(ValidationError):
        ETTransferNew(et_date=date.today())


@pytest.mark.acceptance
def test_U2_3_negative_cl_measure_rejected():
    """Plan U2-3: CL = -5 mm -> rejected. Re-tested against the current code."""
    with pytest.raises(ValidationError):
        ETTransferCreate(et_date=date.today(), cl_measure_mm=-5)


@pytest.mark.acceptance
def test_U3_1_ivm_created_after_valid_opu(client, db_session, admin_user):
    """Plan U3-1: IVM batch created after a valid OPU session."""
    h = _h(client, db_session, "embryologist")
    opu = _opu(client, h, _donor(client, h)["donor_id"])
    ivm = _ivm(client, h, opu["opu_id"])
    assert ivm["opu_id"] == opu["opu_id"]


@pytest.mark.acceptance
def test_U3_2_ivf_without_ivm_rejected(client, db_session, admin_user):
    """Plan U3-2: IVF attempted with no IVM record -> request rejected.

    KNOWN GAP: ivm_batch_id is optional on an IVF batch, so IVF from an OPU
    with no IVM is accepted. A fresh-oocyte IVF path may be intentional; that is
    a product decision (see the results note).
    """
    h = _h(client, db_session, "embryologist")
    opu = _opu(client, h, _donor(client, h)["donor_id"])
    r = _ivf(client, h, opu["opu_id"])
    assert r.status_code in (400, 409, 422), f"IVF without IVM was accepted ({r.status_code})"


@pytest.mark.acceptance
def test_U3_3_embryo_created_after_completed_ivf(client, db_session, admin_user):
    """Plan U3-3: embryo created from a valid IVF batch."""
    h = _h(client, db_session, "embryologist")
    chain = _full_chain(client, h)
    assert chain["embryo"]["ivf_batch_id"] == chain["ivf"]["ivf_batch_id"]


@pytest.mark.acceptance
def test_U4_1_available_embryo_accepted_for_et(client, db_session, admin_user):
    """Plan U4-1: an embryo that is available for transfer is accepted (Transferable)."""
    h = _h(client, db_session, "veterinarian")
    lab = _h(client, db_session, "embryologist")
    chain = _full_chain(client, lab)
    emb = _ok(client.patch(f"/lab/embryos/{chain['embryo']['embryo_id']}/status", headers=lab,
                           json={"status": "Transferable"}), 200)
    rcp = _recipient(client, h)
    _ok(_et(client, h, emb["embryo_id"], rcp["recipient_id"]), 201)


@pytest.mark.acceptance
def test_U4_2a_transferred_embryo_rejected_for_et(client, db_session, admin_user):
    """Plan U4-2: an embryo with status Transferred must not be accepted for ET.

    KNOWN GAP: ET creation does not check the embryo's status.
    """
    h = _h(client, db_session, "veterinarian")
    lab = _h(client, db_session, "embryologist")
    chain = _full_chain(client, lab)
    client.patch(f"/lab/embryos/{chain['embryo']['embryo_id']}/status", headers=lab, json={"status": "Transferred"})
    rcp = _recipient(client, h)
    r = _et(client, h, chain["embryo"]["embryo_id"], rcp["recipient_id"])
    assert r.status_code in (400, 409, 422), f"Transferred embryo accepted for ET ({r.status_code})"


@pytest.mark.acceptance
def test_U4_2b_same_embryo_cannot_join_two_active_et(client, db_session, admin_user):
    """Plan U4-1/4-2 core rule: one embryo may not sit in two active ET events.

    KNOWN GAP: the second ET for the same embryo is accepted.
    """
    h = _h(client, db_session, "veterinarian")
    lab = _h(client, db_session, "embryologist")
    chain = _full_chain(client, lab)
    rcp1, rcp2 = _recipient(client, h), _recipient(client, h)
    _ok(_et(client, h, chain["embryo"]["embryo_id"], rcp1["recipient_id"]), 201)
    r = _et(client, h, chain["embryo"]["embryo_id"], rcp2["recipient_id"])
    assert r.status_code in (400, 409, 422), f"same embryo accepted in a second ET ({r.status_code})"


# ══════════════════════════════════════════════════════════════════════════
# 5.2 Functional testing
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.acceptance
def test_F1_1_admin_login_and_access(client, db_session, admin_user):
    """Plan F1-1: admin logs in and has admin access.

    Dashboard redirect was also checked in the browser (demo admin login).
    """
    user = _mkuser(db_session, "admin", "admin1")
    r = client.post("/auth/login", data={"username": user, "password": PW})
    assert r.status_code == 200, r.text
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/auth/me", headers=h).json()["role"] == "admin"
    assert client.get("/admin/users", headers=h).status_code == 200
    assert client.get("/dashboard/kpis", headers=h).status_code == 200


@pytest.mark.acceptance
def test_F1_2_embryologist_login_and_access(client, db_session, admin_user):
    """Plan F1-2: embryologist logs in; lab access yes, user management no."""
    user = _mkuser(db_session, "embryologist", "emb1")
    r = client.post("/auth/login", data={"username": user, "password": PW})
    assert r.status_code == 200, r.text
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/auth/me", headers=h).json()["role"] == "embryologist"
    donor = _donor(client, _h(client, db_session, "admin"))
    assert client.post("/opu-sessions/", headers=h, json={"donor_id": donor["donor_id"], "opu_date": TODAY}).status_code == 201
    assert client.get("/admin/users", headers=h).status_code == 403


@pytest.mark.acceptance
def test_F1_3_veterinarian_login_and_access(client, db_session, admin_user):
    """Plan F1-3: veterinarian logs in; ET access yes, lab write no."""
    user = _mkuser(db_session, "veterinarian", "vet1")
    r = client.post("/auth/login", data={"username": user, "password": PW})
    assert r.status_code == 200, r.text
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get("/auth/me", headers=h).json()["role"] == "veterinarian"
    assert client.post("/recipients/", headers=h, json={"tag_id": _tag("RCP")}).status_code == 201
    donor = _donor(client, _h(client, db_session, "admin"))
    assert client.post("/opu-sessions/", headers=h, json={"donor_id": donor["donor_id"], "opu_date": TODAY}).status_code == 403


@pytest.mark.acceptance
def test_F1_4_wrong_password_rejected(client, db_session, admin_user):
    """Plan F1-4: wrong password -> invalid-credentials message and no access."""
    user = _mkuser(db_session, "admin", "admin1")
    r = client.post("/auth/login", data={"username": user, "password": "wrong"})
    assert r.status_code == 401
    assert "Invalid username or password" in r.json()["detail"]


@pytest.mark.acceptance
def test_F2_1_create_donor(client, db_session, admin_user):
    """Plan F2-1: valid donor record is saved."""
    h = _h(client, db_session, "embryologist")
    donor = _donor(client, h)
    assert donor["donor_id"] and donor["tag_id"].startswith("DNR-")


@pytest.mark.acceptance
def test_F2_2_search_donor_by_tag(client, db_session, admin_user):
    """Plan F2-2: search by an existing tag returns the matching record."""
    h = _h(client, db_session, "embryologist")
    donor = _donor(client, h)
    body = _ok(client.get("/donors/", headers=h, params={"search": donor["tag_id"]}), 200)
    assert donor["donor_id"] in [d["donor_id"] for d in body["items"]]


@pytest.mark.acceptance
def test_F2_3_open_case_history(client, db_session, admin_user):
    """Plan F2-3: a case shows the linked donor, sire, recipient and stage."""
    lab = _h(client, db_session, "embryologist")
    vet = _h(client, db_session, "veterinarian")
    chain = _full_chain(client, lab)
    rcp = _recipient(client, vet)
    tr = _ok(_et(client, vet, chain["embryo"]["embryo_id"], rcp["recipient_id"]), 201)
    case = _ok(client.get(f"/cases/{tr['transfer_id']}", headers=lab), 200)
    assert case["donor"] is not None and case["recipient"] is not None
    assert case["embryo_stage"] == 7


@pytest.mark.acceptance
def test_F2_4_duplicate_tag_rejected(client, db_session, admin_user):
    """Plan F2-4: a duplicate donor tag is refused with a validation error."""
    h = _h(client, db_session, "embryologist")
    tag = _tag("DUP")
    _ok(client.post("/donors/", headers=h, json={"tag_id": tag}), 201)
    r = client.post("/donors/", headers=h, json={"tag_id": tag})
    assert r.status_code == 409, r.text


@pytest.mark.acceptance
def test_F3_1_create_opu_session(client, db_session, admin_user):
    """Plan F3-1: OPU session saved against the donor."""
    h = _h(client, db_session, "embryologist")
    donor = _donor(client, h)
    opu = _opu(client, h, donor["donor_id"])
    assert opu["donor_id"] == donor["donor_id"]


@pytest.mark.acceptance
def test_F3_2_create_ivm_linked_to_opu(client, db_session, admin_user):
    """Plan F3-2: IVM batch linked to the OPU session."""
    h = _h(client, db_session, "embryologist")
    opu = _opu(client, h, _donor(client, h)["donor_id"])
    assert _ivm(client, h, opu["opu_id"])["opu_id"] == opu["opu_id"]


@pytest.mark.acceptance
def test_F3_3_create_ivf_linked_to_ivm(client, db_session, admin_user):
    """Plan F3-3: IVF linked to the completed IVM batch."""
    h = _h(client, db_session, "embryologist")
    opu = _opu(client, h, _donor(client, h)["donor_id"])
    ivm = _ivm(client, h, opu["opu_id"])
    ivf = _ok(_ivf(client, h, opu["opu_id"], ivm_id=ivm["ivm_batch_id"]), 201)
    assert ivf["ivm_batch_id"] == ivm["ivm_batch_id"]


@pytest.mark.acceptance
def test_F3_4_embryos_linked_to_ivf(client, db_session, admin_user):
    """Plan F3-4: embryos linked to the IVF batch."""
    h = _h(client, db_session, "embryologist")
    chain = _full_chain(client, h)
    assert chain["embryo"]["ivf_batch_id"] == chain["ivf"]["ivf_batch_id"]


@pytest.mark.acceptance
def test_F3_5_stage_out_of_order_gives_error(client, db_session, admin_user):
    """Plan F3-5: IVF without IVM -> validation error. Same gap as U3-2."""
    h = _h(client, db_session, "embryologist")
    opu = _opu(client, h, _donor(client, h)["donor_id"])
    r = _ivf(client, h, opu["opu_id"])
    assert r.status_code in (400, 409, 422), f"out-of-order IVF accepted ({r.status_code})"


@pytest.mark.acceptance
def test_F4_1_valid_et_data_gives_prediction(client, db_session, admin_user):
    """Plan F4-1: CL = 18 mm, stage = 7 -> probability returned."""
    h = _h(client, db_session, "veterinarian")
    r = client.post("/predict/pregnancy", headers=h, json={"cl_measure_mm": 18, "embryo_stage": 7})
    body = _ok(r, 200)
    assert 0.0 <= body["probability"] <= 1.0 and body["risk_band"]


@pytest.mark.acceptance
def test_F4_2_incomplete_prediction_input_rejected(client, db_session, admin_user):
    """Plan F4-2: required prediction fields missing -> validation error."""
    h = _h(client, db_session, "veterinarian")
    r = client.post("/predict/pregnancy", headers=h, json={"embryo_stage": 7})
    assert r.status_code == 422


@pytest.mark.acceptance
def test_F4_3_invalid_prediction_input_blocked(client, db_session, admin_user):
    """Plan F4-3: CL = -5 mm -> validation error and no prediction stored."""
    h = _h(client, db_session, "veterinarian")
    before = db_session.query(Prediction).count()
    r = client.post("/predict/pregnancy", headers=h, json={"cl_measure_mm": -5, "embryo_stage": 7})
    assert r.status_code == 422
    assert db_session.query(Prediction).count() == before


@pytest.mark.acceptance
def test_F5_1_upload_valid_image(client, db_session, admin_user):
    """Plan F5-1: a supported JPEG is accepted and stored."""
    h = _h(client, db_session, "embryologist")
    chain = _full_chain(client, h)
    r = client.post("/grade/upload", headers=h, data={"embryo_id": str(chain["embryo"]["embryo_id"])},
                    files={"image": ("blq1.jpg", _image_bytes(), "image/jpeg")})
    assert "image_id" in _ok(r, 200)


@pytest.mark.acceptance
def test_F5_2_grade_valid_image(client, db_session, admin_user):
    """Plan F5-2: a valid image gets a grade and probabilities."""
    h = _h(client, db_session, "embryologist")
    chain = _full_chain(client, h)
    body = _ok(client.post(f"/grade/embryo/{chain['embryo']['embryo_id']}", headers=h,
                           files={"image": ("blq1.jpg", _image_bytes(), "image/jpeg")}), 200)
    assert body["predicted_grade"] in (1, 2, 3)
    assert body["probabilities"]


@pytest.mark.acceptance
def test_F5_3_unsupported_file_rejected(client, db_session, admin_user):
    """Plan F5-3: a non-image file -> validation error.

    KNOWN GAP: the upload endpoint documents "any file format" and stores a
    text file as an embryo image.
    """
    h = _h(client, db_session, "embryologist")
    chain = _full_chain(client, h)
    r = client.post("/grade/upload", headers=h, data={"embryo_id": str(chain["embryo"]["embryo_id"])},
                    files={"image": ("notes.txt", b"this is not an image", "text/plain")})
    assert r.status_code in (400, 415, 422), f"text file accepted as an embryo image ({r.status_code})"


@pytest.mark.acceptance
def test_F5_4_save_grade_linked_to_embryo(client, db_session, admin_user):
    """Plan F5-4: the AI result is saved against the embryo; the manual grade is untouched."""
    h = _h(client, db_session, "embryologist")
    chain = _full_chain(client, h)
    emb_id = chain["embryo"]["embryo_id"]
    client.put(f"/embryos/{emb_id}", headers=h, json={"grade": 2})
    _ok(client.post(f"/grade/embryo/{emb_id}", headers=h,
                    files={"image": ("blq1.jpg", _image_bytes(), "image/jpeg")}), 200)
    cmp = _ok(client.get(f"/grade/embryo/{emb_id}/assessments", headers=h), 200)
    assert len(cmp["ai_assessments"]) == 1
    assert cmp["manual_grade"] == 2
    assert db_session.get(Embryo, emb_id).grade == 2


@pytest.mark.acceptance
def test_F6_1_dashboard_kpis_after_login(client, db_session, admin_user):
    """Plan F6-1: the dashboard returns KPI cards for an authenticated user."""
    h = _h(client, db_session, "admin")
    kpis = _ok(client.get("/dashboard/kpis", headers=h), 200)["kpis"]
    assert len(kpis) > 0


@pytest.mark.acceptance
def test_F6_2_new_et_record_updates_counts(client, db_session, admin_user):
    """Plan F6-2: a new ET record increases the transfer count on the dashboard."""
    admin = _h(client, db_session, "admin")
    before = _ok(client.get("/dashboard/charts", headers=admin), 200)["kpis"]["total_transfers"]
    vet = _h(client, db_session, "veterinarian")
    lab = _h(client, db_session, "embryologist")
    chain = _full_chain(client, lab)
    _ok(_et(client, vet, chain["embryo"]["embryo_id"], _recipient(client, vet)["recipient_id"]), 201)
    after = _ok(client.get("/dashboard/charts", headers=admin), 200)["kpis"]["total_transfers"]
    assert after == before + 1


@pytest.mark.acceptance
def test_F6_3_pregnancy_outcome_updates_statistics(client, db_session, admin_user):
    """Plan F6-3: recording a pregnant outcome increases the pregnant count."""
    admin = _h(client, db_session, "admin")
    vet = _h(client, db_session, "veterinarian")
    lab = _h(client, db_session, "embryologist")
    chain = _full_chain(client, lab)
    tr = _ok(_et(client, vet, chain["embryo"]["embryo_id"], _recipient(client, vet)["recipient_id"]), 201)
    before = _ok(client.get("/dashboard/charts", headers=admin), 200)["kpis"]["pregnant"]
    _ok(_pc(client, vet, tr["transfer_id"], "Pregnant"), 201)
    after = _ok(client.get("/dashboard/charts", headers=admin), 200)["kpis"]["pregnant"]
    assert after == before + 1


@pytest.mark.acceptance
def test_F6_4_dashboard_content_by_role(client, db_session, admin_user):
    """Plan F6-4: each role sees only its dashboard content (server-enforced)."""
    res = _h(client, db_session, "researcher")
    emb = _h(client, db_session, "embryologist")
    assert client.get("/dashboard/operations", headers=res).status_code == 403
    assert client.get("/dashboard/operations", headers=emb).status_code == 200
    assert client.get("/dashboard/performance?dimension=protocol", headers=emb).status_code == 403


@pytest.mark.acceptance
def test_F7_1_create_et_record(client, db_session, admin_user):
    """Plan F7-1: a valid embryo and recipient create an ET record."""
    vet = _h(client, db_session, "veterinarian")
    lab = _h(client, db_session, "embryologist")
    chain = _full_chain(client, lab)
    tr = _ok(_et(client, vet, chain["embryo"]["embryo_id"], _recipient(client, vet)["recipient_id"]), 201)
    assert tr["embryo_id"] == chain["embryo"]["embryo_id"]


@pytest.mark.acceptance
def test_F7_2_et_without_recipient_rejected(client, db_session, admin_user):
    """Plan F7-2: an ET with no recipient -> validation error.

    KNOWN GAP: recipient_id is optional on the transfer record.
    """
    vet = _h(client, db_session, "veterinarian")
    lab = _h(client, db_session, "embryologist")
    chain = _full_chain(client, lab)
    r = _et(client, vet, chain["embryo"]["embryo_id"], None)
    assert r.status_code in (400, 422), f"ET accepted without a recipient ({r.status_code})"


@pytest.mark.acceptance
def test_F7_3_reuse_transferred_embryo_blocked(client, db_session, admin_user):
    """Plan F7-3: reusing a transferred embryo is blocked. Same gap as U4-2b."""
    vet = _h(client, db_session, "veterinarian")
    lab = _h(client, db_session, "embryologist")
    chain = _full_chain(client, lab)
    _ok(_et(client, vet, chain["embryo"]["embryo_id"], _recipient(client, vet)["recipient_id"]), 201)
    r = _et(client, vet, chain["embryo"]["embryo_id"], _recipient(client, vet)["recipient_id"])
    assert r.status_code in (400, 409, 422), f"transferred embryo reused ({r.status_code})"


@pytest.mark.acceptance
def test_F7_4_pc1_pregnant_updates_et(client, db_session, admin_user):
    """Plan F7-4: PC1 = Pregnant updates the ET record."""
    vet = _h(client, db_session, "veterinarian")
    lab = _h(client, db_session, "embryologist")
    chain = _full_chain(client, lab)
    tr = _ok(_et(client, vet, chain["embryo"]["embryo_id"], _recipient(client, vet)["recipient_id"]), 201)
    _ok(_pc(client, vet, tr["transfer_id"], "Pregnant"), 201)
    db_session.expire_all()
    assert db_session.get(ETTransfer, tr["transfer_id"]).pc1_result == "Pregnant"


@pytest.mark.acceptance
def test_F7_5_recheck_keeps_et_pending(client, db_session, admin_user):
    """Plan F7-5: PC1 = Recheck leaves the ET pending, not resolved."""
    vet = _h(client, db_session, "veterinarian")
    lab = _h(client, db_session, "embryologist")
    chain = _full_chain(client, lab)
    tr = _ok(_et(client, vet, chain["embryo"]["embryo_id"], _recipient(client, vet)["recipient_id"]), 201)
    _ok(_pc(client, vet, tr["transfer_id"], "Recheck"), 201)
    db_session.expire_all()
    assert db_session.get(ETTransfer, tr["transfer_id"]).pc1_result == "Recheck"


# ══════════════════════════════════════════════════════════════════════════
# 5.3 Business rules
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.acceptance
def test_BR01_unauthenticated_access_rejected(client):
    """BR-01: a protected endpoint without a session is refused (API level).

    The browser redirect to login was checked separately (ProtectedRoute).
    """
    assert client.get("/analytics/kpis").status_code == 401


@pytest.mark.acceptance
def test_BR02_admin_opens_user_management(client, db_session, admin_user):
    """BR-02: admin can open user management."""
    h = _h(client, db_session, "admin")
    assert client.get("/admin/users", headers=h).status_code == 200


@pytest.mark.acceptance
def test_BR03_embryologist_records_opu_then_ivm(client, db_session, admin_user):
    """BR-03: an embryologist records a valid OPU -> IVM sequence."""
    h = _h(client, db_session, "embryologist")
    opu = _opu(client, h, _donor(client, h)["donor_id"])
    assert _ivm(client, h, opu["opu_id"])["ivm_batch_id"]


@pytest.mark.acceptance
def test_BR04_ivf_without_ivm_blocked(client, db_session, admin_user):
    """BR-04: IVF without IVM is blocked. Same gap as U3-2."""
    h = _h(client, db_session, "embryologist")
    opu = _opu(client, h, _donor(client, h)["donor_id"])
    r = _ivf(client, h, opu["opu_id"])
    assert r.status_code in (400, 409, 422), f"IVF without IVM was allowed ({r.status_code})"


@pytest.mark.acceptance
def test_BR05_invalid_prediction_value_gives_no_prediction(client, db_session, admin_user):
    """BR-05: an invalid prediction value gives a validation error and stores nothing."""
    h = _h(client, db_session, "veterinarian")
    before = db_session.query(Prediction).count()
    r = client.post("/predict/pregnancy", headers=h, json={"cl_measure_mm": 999, "embryo_stage": 7})
    assert r.status_code == 422
    assert db_session.query(Prediction).count() == before


@pytest.mark.acceptance
def test_BR06_invalid_embryo_image_blocks_grading(client, db_session, admin_user):
    """BR-06: an image that is not a blastocyst is refused and nothing is saved."""
    h = _h(client, db_session, "embryologist")
    chain = _full_chain(client, h)
    r = client.post(f"/grade/embryo/{chain['embryo']['embryo_id']}", headers=h,
                    files={"image": ("bad.jpg", b"not an image at all", "image/jpeg")})
    assert r.status_code in (400, 415, 422)
    cmp = _ok(client.get(f"/grade/embryo/{chain['embryo']['embryo_id']}/assessments", headers=h), 200)
    assert cmp["ai_assessments"] == []


@pytest.mark.acceptance
def test_BR07_transferred_embryo_blocked_for_et(client, db_session, admin_user):
    """BR-07: a vet selecting an already transferred embryo is blocked. Same gap as U4-2b."""
    vet = _h(client, db_session, "veterinarian")
    lab = _h(client, db_session, "embryologist")
    chain = _full_chain(client, lab)
    _ok(_et(client, vet, chain["embryo"]["embryo_id"], _recipient(client, vet)["recipient_id"]), 201)
    r = _et(client, vet, chain["embryo"]["embryo_id"], _recipient(client, vet)["recipient_id"])
    assert r.status_code in (400, 409, 422), f"already-transferred embryo selected ({r.status_code})"


@pytest.mark.acceptance
def test_BR08_valid_pc1_outcome_updates_et(client, db_session, admin_user):
    """BR-08: a valid PC1 outcome updates the ET record."""
    vet = _h(client, db_session, "veterinarian")
    lab = _h(client, db_session, "embryologist")
    chain = _full_chain(client, lab)
    tr = _ok(_et(client, vet, chain["embryo"]["embryo_id"], _recipient(client, vet)["recipient_id"]), 201)
    _ok(_pc(client, vet, tr["transfer_id"], "Open"), 201)
    db_session.expire_all()
    assert db_session.get(ETTransfer, tr["transfer_id"]).pc1_result == "Open"


# ══════════════════════════════════════════════════════════════════════════
# 5.4 Integration testing
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.acceptance
def test_I1_1_opu_linked_to_donor(client, db_session, admin_user):
    """Integration 1.1: an OPU session created for a donor is linked to that donor."""
    h = _h(client, db_session, "embryologist")
    donor = _donor(client, h)
    opu = _opu(client, h, donor["donor_id"])
    assert _ok(client.get(f"/opu-sessions/{opu['opu_id']}", headers=h), 200)["donor_id"] == donor["donor_id"]


@pytest.mark.acceptance
def test_I1_2_opu_ivm_ivf_each_linked(client, db_session, admin_user):
    """Integration 1.2: OPU -> IVM -> IVF, each linked to the one before."""
    h = _h(client, db_session, "embryologist")
    chain = _full_chain(client, h)
    ivf = _ok(client.get(f"/ivf-batches/{chain['ivf']['ivf_batch_id']}", headers=h), 200)
    assert ivf["opu_id"] == chain["opu"]["opu_id"]
    assert ivf["ivm_batch_id"] == chain["ivm"]["ivm_batch_id"]


@pytest.mark.acceptance
def test_I1_3_embryo_traceable_to_donor_sire_and_ivf(client, db_session, admin_user):
    """Integration 1.3: from an embryo, the donor, sire and IVF batch are reachable.

    Traced through the links the records hold: embryo -> IVF batch -> OPU -> donor,
    and IVF batch -> sire.
    """
    h = _h(client, db_session, "embryologist")
    chain = _full_chain(client, h)
    emb = _ok(client.get(f"/embryos/{chain['embryo']['embryo_id']}", headers=h), 200)
    ivf = _ok(client.get(f"/ivf-batches/{emb['ivf_batch_id']}", headers=h), 200)
    opu = _ok(client.get(f"/opu-sessions/{ivf['opu_id']}", headers=h), 200)
    assert opu["donor_id"] == chain["donor"]["donor_id"]
    assert ivf["sire_id"] == chain["sire"]["sire_id"]


@pytest.mark.acceptance
def test_I2_1_lab_embryo_loads_in_grading(client, db_session, admin_user):
    """Integration 2.1: an embryo created in the lab is available to the grading step."""
    h = _h(client, db_session, "embryologist")
    chain = _full_chain(client, h)
    assert _ok(client.get(f"/embryos/{chain['embryo']['embryo_id']}", headers=h), 200)["embryo_id"]
    assert _ok(client.get(f"/grade/embryo/{chain['embryo']['embryo_id']}/assessments", headers=h), 200)


@pytest.mark.acceptance
def test_I2_2_grading_result_linked_to_same_embryo(client, db_session, admin_user):
    """Integration 2.2: the grading result is recorded against the same embryo."""
    h = _h(client, db_session, "embryologist")
    chain = _full_chain(client, h)
    emb_id = chain["embryo"]["embryo_id"]
    _ok(client.post(f"/grade/embryo/{emb_id}", headers=h,
                    files={"image": ("blq1.jpg", _image_bytes(), "image/jpeg")}), 200)
    cmp = _ok(client.get(f"/grade/embryo/{emb_id}/assessments", headers=h), 200)
    assert all(a["embryo_id"] == emb_id for a in cmp["ai_assessments"]) and cmp["ai_assessments"]


@pytest.mark.acceptance
def test_I3_1_available_embryo_and_recipient_create_et(client, db_session, admin_user):
    """Integration 3.1: an available embryo and a recipient create an ET record."""
    vet = _h(client, db_session, "veterinarian")
    lab = _h(client, db_session, "embryologist")
    chain = _full_chain(client, lab)
    rcp = _recipient(client, vet)
    tr = _ok(_et(client, vet, chain["embryo"]["embryo_id"], rcp["recipient_id"]), 201)
    assert tr["recipient_id"] == rcp["recipient_id"]


@pytest.mark.acceptance
def test_I3_2_case_history_shows_production_and_et(client, db_session, admin_user):
    """Integration 3.2: the case shows the embryo's production and the ET event together."""
    vet = _h(client, db_session, "veterinarian")
    lab = _h(client, db_session, "embryologist")
    chain = _full_chain(client, lab)
    tr = _ok(_et(client, vet, chain["embryo"]["embryo_id"], _recipient(client, vet)["recipient_id"]), 201)
    case = _ok(client.get(f"/cases/{tr['transfer_id']}", headers=lab), 200)
    assert case["embryo_stage"] == 7 and case["donor"] is not None
    timeline = _ok(client.get(f"/case-timeline/{tr['transfer_id']}/timeline", headers=lab), 200)
    assert timeline


@pytest.mark.acceptance
def test_I4_1_prediction_opened_from_et_case(client, db_session, admin_user):
    """Integration 4.1: a prediction is run for an ET record and linked to it."""
    vet = _h(client, db_session, "veterinarian")
    lab = _h(client, db_session, "embryologist")
    chain = _full_chain(client, lab)
    tr = _ok(_et(client, vet, chain["embryo"]["embryo_id"], _recipient(client, vet)["recipient_id"]), 201)
    body = _ok(client.post("/predict/pregnancy", headers=vet,
                           json={"cl_measure_mm": 18, "embryo_stage": 7, "transfer_id": tr["transfer_id"]}), 200)
    row = db_session.query(Prediction).filter(Prediction.request_id == body["request_id"]).first()
    assert row is not None and row.transfer_id == tr["transfer_id"]


@pytest.mark.acceptance
def test_I4_2_prediction_shown_on_case(client, db_session, admin_user):
    """Integration 4.2: the prediction is associated with the case."""
    vet = _h(client, db_session, "veterinarian")
    lab = _h(client, db_session, "embryologist")
    chain = _full_chain(client, lab)
    tr = _ok(_et(client, vet, chain["embryo"]["embryo_id"], _recipient(client, vet)["recipient_id"]), 201)
    client.post("/predict/pregnancy", headers=vet,
                json={"cl_measure_mm": 18, "embryo_stage": 7, "transfer_id": tr["transfer_id"]})
    case = _ok(client.get(f"/cases/{tr['transfer_id']}", headers=lab), 200)
    assert case["pregnancy_prediction"] is not None


@pytest.mark.acceptance
def test_I5_1_new_et_updates_total(client, db_session, admin_user):
    """Integration 5.1: a new ET event updates the total on the dashboard."""
    test_F6_2_new_et_record_updates_counts(client, db_session, admin_user)


@pytest.mark.acceptance
def test_I5_2_pregnant_outcome_updates_count(client, db_session, admin_user):
    """Integration 5.2: a pregnant outcome updates the pregnancy count."""
    test_F6_3_pregnancy_outcome_updates_statistics(client, db_session, admin_user)


@pytest.mark.acceptance
def test_I5_3_refresh_shows_latest_values(client, db_session, admin_user):
    """Integration 5.3: a refreshed dashboard returns the stored values."""
    admin = _h(client, db_session, "admin")
    first = _ok(client.get("/dashboard/charts", headers=admin), 200)["kpis"]
    second = _ok(client.get("/dashboard/charts", headers=admin), 200)["kpis"]
    assert first == second


@pytest.mark.acceptance
def test_I6_1_embryologist_role_grants_lab_access(client, db_session, admin_user):
    """Integration 6.1: an admin assigns Embryologist; lab access is then allowed."""
    admin = _h(client, db_session, "admin")
    target = _mkuser(db_session, "researcher")
    uid = db_session.query(User).filter(User.username == target).first().user_id
    _ok(client.put(f"/admin/users/{uid}", headers=admin, json={"role": "embryologist"}), 200)
    r = client.post("/auth/login", data={"username": target, "password": PW})
    assert r.status_code == 200, r.text
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    donor = _donor(client, admin)
    assert client.post("/opu-sessions/", headers=h, json={"donor_id": donor["donor_id"], "opu_date": TODAY}).status_code == 201


@pytest.mark.acceptance
def test_I6_2_veterinarian_role_grants_et_access(client, db_session, admin_user):
    """Integration 6.2: an admin assigns Veterinarian; ET access is then allowed."""
    admin = _h(client, db_session, "admin")
    target = _mkuser(db_session, "researcher")
    uid = db_session.query(User).filter(User.username == target).first().user_id
    _ok(client.put(f"/admin/users/{uid}", headers=admin, json={"role": "veterinarian"}), 200)
    r = client.post("/auth/login", data={"username": target, "password": PW})
    assert r.status_code == 200, r.text
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.post("/recipients/", headers=h, json={"tag_id": _tag("RCP")}).status_code == 201


@pytest.mark.acceptance
def test_I6_3_deactivated_user_loses_access(client, db_session, admin_user):
    """Integration 6.3: after deactivation, existing and new sessions are refused."""
    admin = _h(client, db_session, "admin")
    target = _mkuser(db_session, "embryologist")
    old = client.post("/auth/login", data={"username": target, "password": PW}).json()["access_token"]
    uid = db_session.query(User).filter(User.username == target).first().user_id
    assert client.delete(f"/admin/users/{uid}", headers=admin).status_code == 204
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {old}"}).status_code in (401, 403)
    assert client.post("/auth/login", data={"username": target, "password": PW}).status_code == 403
