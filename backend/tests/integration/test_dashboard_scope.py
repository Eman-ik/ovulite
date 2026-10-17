"""Each role gets its own homepage dashboard, enforced by the server.

Checked against the API directly, as a client that bypasses the screen would
call it. Admin sees everything; embryologist sees lab; veterinarian sees ET;
researcher sees outcomes and no daily operations or pipeline.
"""

from __future__ import annotations

import uuid

import pytest

from app.auth.security import hash_password
from app.models.user import User

PASSWORD = "Str0ng!Passw0rd"

LAB_KPIS = {"oocytes_recovered", "maturation_rate", "cleavage_rate", "blastocyst_rate"}
ET_KPIS = {"transferable_embryos", "transfers_completed", "pregnancy_rate", "model_auc"}
LAB_FUNNEL = {"Oocytes Recovered", "Mature Oocytes", "Cleaved Embryos", "Blastocysts"}
ET_FUNNEL = {"Transferable Embryos", "Transfers", "Pregnancies", "Ongoing Pregnancies"}
LAB_OPS = {"opu_sessions_today", "ivf_batches_in_culture", "embryos_pending_grading"}
ET_OPS = {"transfers_scheduled_today", "pregnancy_checks_due", "predictions_pending_outcome"}
ALL_OPS = LAB_OPS | ET_OPS


def _headers(client, db_session, role: str) -> dict:
    admin = db_session.query(User).filter(User.username == "admin").first()
    username = f"dash_{role}_{uuid.uuid4().hex[:6]}"
    db_session.add(User(username=username, password_hash=hash_password(PASSWORD), role=role,
                        active=True, organization_id=admin.organization_id))
    db_session.commit()
    r = client.post("/auth/login", data={"username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _kpi_keys(client, h) -> set[str]:
    r = client.get("/dashboard/kpis", headers=h)
    assert r.status_code == 200, r.text
    return {k["key"] for k in r.json()["kpis"]}


def _ops(client, h) -> dict:
    r = client.get("/dashboard/operations", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


# ── Admin: everything ──────────────────────────────────────────────────────

@pytest.mark.integration
def test_admin_sees_every_section(client, db_session, admin_user):
    h = _headers(client, db_session, "admin")
    keys = _kpi_keys(client, h)
    assert LAB_KPIS <= keys and ET_KPIS <= keys
    ops = _ops(client, h)
    assert all(ops[f] is not None for f in ALL_OPS)
    for dim in ("donor", "sire", "protocol", "technician"):
        assert client.get(f"/dashboard/performance?dimension={dim}", headers=h).status_code == 200


# ── Embryologist: lab only ─────────────────────────────────────────────────

@pytest.mark.integration
def test_embryologist_kpis_are_lab_only(client, db_session, admin_user):
    h = _headers(client, db_session, "embryologist")
    keys = _kpi_keys(client, h)
    assert keys <= LAB_KPIS, f"embryologist was sent non-lab KPIs: {keys - LAB_KPIS}"
    assert keys, "embryologist should receive its lab KPIs"


@pytest.mark.integration
def test_embryologist_funnel_is_lab_stages(client, db_session, admin_user):
    h = _headers(client, db_session, "embryologist")
    stages = {s["name"] for s in client.get("/dashboard/funnel", headers=h).json()["stages"]}
    assert stages <= LAB_FUNNEL, f"embryologist was sent ET stages: {stages - LAB_FUNNEL}"


@pytest.mark.integration
def test_embryologist_operations_omit_transfer_fields(client, db_session, admin_user):
    h = _headers(client, db_session, "embryologist")
    ops = _ops(client, h)
    for f in LAB_OPS:
        assert ops[f] is not None, f
    for f in ET_OPS:
        assert ops[f] is None, f"embryologist was sent {f}"


@pytest.mark.integration
def test_embryologist_cannot_read_protocol_performance(client, db_session, admin_user):
    h = _headers(client, db_session, "embryologist")
    assert client.get("/dashboard/performance?dimension=protocol", headers=h).status_code == 403
    assert client.get("/dashboard/performance?dimension=donor", headers=h).status_code == 200


# ── Veterinarian: ET only ──────────────────────────────────────────────────

@pytest.mark.integration
def test_veterinarian_kpis_are_et_only(client, db_session, admin_user):
    h = _headers(client, db_session, "veterinarian")
    keys = _kpi_keys(client, h)
    assert keys <= ET_KPIS, f"veterinarian was sent non-ET KPIs: {keys - ET_KPIS}"


@pytest.mark.integration
def test_veterinarian_operations_are_et_only(client, db_session, admin_user):
    h = _headers(client, db_session, "veterinarian")
    ops = _ops(client, h)
    for f in ET_OPS:
        assert ops[f] is not None, f
    for f in LAB_OPS:
        assert ops[f] is None, f"veterinarian was sent {f}"


@pytest.mark.integration
def test_veterinarian_cannot_read_donor_performance(client, db_session, admin_user):
    h = _headers(client, db_session, "veterinarian")
    assert client.get("/dashboard/performance?dimension=donor", headers=h).status_code == 403
    assert client.get("/dashboard/performance?dimension=protocol", headers=h).status_code == 200


# ── Researcher: outcomes, no operations ────────────────────────────────────

@pytest.mark.integration
def test_researcher_has_no_operations_or_pipeline(client, db_session, admin_user):
    h = _headers(client, db_session, "researcher")
    assert client.get("/dashboard/operations", headers=h).status_code == 403
    assert client.get("/dashboard/pipeline", headers=h).status_code == 403


@pytest.mark.integration
def test_researcher_reads_outcome_performance_and_kpis(client, db_session, admin_user):
    h = _headers(client, db_session, "researcher")
    assert "pregnancy_rate" in _kpi_keys(client, h)
    for dim in ("donor", "sire", "protocol", "technician"):
        assert client.get(f"/dashboard/performance?dimension={dim}", headers=h).status_code == 200


# ── Unknown role: refused at the database ──────────────────────────────────

@pytest.mark.integration
def test_unrecognised_role_cannot_be_stored(client, db_session, admin_user):
    """The role constraint is the gate: a role outside the four cannot exist, so
    it can never receive dashboard data. Fail-closed in code covers any row the
    constraint somehow missed (see DASHBOARD_SCOPE)."""
    from sqlalchemy.exc import IntegrityError
    admin = db_session.query(User).filter(User.username == "admin").first()
    db_session.add(User(username=f"dash_odd_{uuid.uuid4().hex[:6]}", password_hash=hash_password(PASSWORD),
                        role="technical_staff", active=True, organization_id=admin.organization_id))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
