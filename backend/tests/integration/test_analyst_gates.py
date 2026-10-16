"""The analysis surfaces are readable only by admin and researcher, on the server.

The frontend has always hidden these screens from other roles. Hiding alone is
not access control: a client that calls the API directly got the same data.
These tests call the endpoints as each of the four roles and check the refusal.
"""

from __future__ import annotations

import uuid

import pytest

from app.auth.security import hash_password
from app.models.user import User

ANALYST_GETS = [
    "/analytics/kpis",
    "/analytics/funnel",
    "/analytics/donors",
    "/research/donor-sire",
    "/research/protocols",
    "/dashboard/charts",
    "/dashboard/data-quality",
    "/monitoring/metrics",
    "/monitoring/retrain-jobs",
]

PASSWORD = "Str0ng!Passw0rd"


def _login_as(client, db_session, admin_user, role: str) -> dict:
    username = f"gate_{role}_{uuid.uuid4().hex[:6]}"
    admin = db_session.query(User).filter(User.username == "admin").first()
    db_session.add(User(
        username=username,
        password_hash=hash_password(PASSWORD),
        role=role,
        active=True,
        organization_id=admin.organization_id,
    ))
    db_session.commit()
    r = client.post("/auth/login", data={"username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.integration
@pytest.mark.parametrize("path", ANALYST_GETS)
@pytest.mark.parametrize("role", ["embryologist", "veterinarian"])
def test_clinical_roles_are_refused_analysis_reads(client, db_session, admin_user, path, role):
    headers = _login_as(client, db_session, admin_user, role)
    r = client.get(path, headers=headers)
    assert r.status_code == 403, f"{role} reached {path}: {r.status_code}"


@pytest.mark.integration
@pytest.mark.parametrize("path", ANALYST_GETS)
def test_researcher_can_read_analysis(client, db_session, admin_user, path):
    headers = _login_as(client, db_session, admin_user, "researcher")
    r = client.get(path, headers=headers)
    assert r.status_code == 200, f"researcher was refused {path}: {r.status_code} {r.text[:200]}"


@pytest.mark.integration
def test_refusal_names_the_required_roles(client, db_session, admin_user):
    headers = _login_as(client, db_session, admin_user, "veterinarian")
    r = client.get("/analytics/kpis", headers=headers)
    assert r.status_code == 403
    assert "admin" in r.json()["detail"] and "researcher" in r.json()["detail"]
