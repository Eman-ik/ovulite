"""Session revocation must end the old sessions and must not end the new one.

Regression for a defect where the revocation stamp was one second in the
future and tokens carried whole-second issue times. A login made straight after
a password reset or a role change was refused with 401, because it fell inside
that window. Tokens now carry a sub-second issue time, and the stamp is the
current instant.
"""

from __future__ import annotations

import uuid

import pytest

from app.auth.security import hash_password
from app.models.user import User

PW = "Str0ng!Passw0rd"
NEW_PW = "An0ther!Passw0rd"


def _mkuser(db, role: str, password: str = PW) -> str:
    admin = db.query(User).filter(User.username == "admin").first()
    name = f"rev_{role}_{uuid.uuid4().hex[:6]}"
    db.add(User(username=name, password_hash=hash_password(password), role=role,
                active=True, organization_id=admin.organization_id))
    db.commit()
    return name


def _login(client, name: str, password: str = PW) -> dict:
    r = client.post("/auth/login", data={"username": name, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.integration
def test_login_immediately_after_reset_works(client, db_session, admin_user):
    name = _mkuser(db_session, "researcher")
    user = db_session.query(User).filter(User.username == name).first()
    user.email = f"{name}@example.com"
    db_session.commit()
    old = _login(client, name)
    token = client.post("/auth/forgot-password", json={"email": user.email}).json()["reset_token"]
    assert client.post("/auth/reset-password",
                       json={"reset_token": token, "new_password": NEW_PW}).status_code == 200
    # Old session is gone...
    assert client.get("/auth/me", headers=old).status_code == 401
    # ...and a login straight after the reset is accepted, with a working token.
    fresh = _login(client, name, NEW_PW)
    assert client.get("/auth/me", headers=fresh).status_code == 200


@pytest.mark.integration
def test_login_immediately_after_role_change_works(client, db_session, admin_user):
    admin = _login(client, "admin", "ovulite2026")
    name = _mkuser(db_session, "researcher")
    uid = db_session.query(User).filter(User.username == name).first().user_id
    assert client.put(f"/admin/users/{uid}", headers=admin, json={"role": "veterinarian"}).status_code == 200
    fresh = _login(client, name)
    assert client.get("/auth/me", headers=fresh).json()["role"] == "veterinarian"


@pytest.mark.integration
def test_logout_all_then_immediate_login_works(client, db_session, admin_user):
    name = _mkuser(db_session, "researcher")
    old = _login(client, name)
    assert client.post("/auth/logout-all", headers=old).status_code == 200
    assert client.get("/auth/me", headers=old).status_code == 401
    fresh = _login(client, name)
    assert client.get("/auth/me", headers=fresh).status_code == 200


@pytest.mark.integration
def test_change_password_keeps_the_new_session(client, db_session, admin_user):
    name = _mkuser(db_session, "researcher")
    old = _login(client, name)
    changed = client.post("/auth/change-password", headers=old,
                          json={"current_password": PW, "new_password": NEW_PW})
    assert changed.status_code == 200, changed.text
    assert client.get("/auth/me", headers=old).status_code == 401
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {changed.json()['access_token']}"}).status_code == 200
