"""The ET data-entry page uploads through /import. Its gate must match the page:
a veterinarian who can open Data Entry must be able to submit to it."""

from __future__ import annotations

import uuid

import pytest

from app.auth.security import hash_password
from app.models.user import User

PASSWORD = "Str0ng!Passw0rd"


def _login_as(client, db_session, role: str) -> dict:
    admin = db_session.query(User).filter(User.username == "admin").first()
    username = f"imp_{role}_{uuid.uuid4().hex[:6]}"
    db_session.add(User(username=username, password_hash=hash_password(PASSWORD), role=role,
                        active=True, organization_id=admin.organization_id))
    db_session.commit()
    r = client.post("/auth/login", data={"username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _post_empty_file(client, headers):
    # A real request with no file: an authorised caller gets 422 (missing field);
    # a refused one gets 403 before that check runs.
    return client.post("/import/file", headers=headers)


@pytest.mark.integration
@pytest.mark.parametrize("role", ["veterinarian", "admin"])
def test_et_roles_can_use_the_data_entry_upload(client, db_session, admin_user, role):
    headers = _login_as(client, db_session, role)
    assert _post_empty_file(client, headers).status_code == 422


@pytest.mark.integration
@pytest.mark.parametrize("role", ["researcher", "embryologist"])
def test_other_roles_cannot_upload_clinical_files(client, db_session, admin_user, role):
    headers = _login_as(client, db_session, role)
    assert _post_empty_file(client, headers).status_code == 403
