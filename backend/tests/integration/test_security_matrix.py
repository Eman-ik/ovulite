"""Automated RBAC, token-lifecycle and organization-isolation matrix.

RBAC is checked against the routes the app actually serves. Every mutating route
that declares a role gate is called once per role, and a role outside the gate
must get 403 before the handler runs. Mutating routes with no gate must appear in
UNGATED_ALLOWED with a reason, so a new unguarded write fails this file.
"""

from __future__ import annotations

import re
import uuid
from datetime import timedelta

import jwt
import pytest

from app.api import auth as auth_api
from app.auth.security import ALGORITHM, create_access_token, hash_password
from app.main import app
from app.models.organization import Organization
from app.models.user import User

PASSWORD = "Str0ng!Passw0rd"
# The seeded admin's password, set for the test run in conftest.py.
ADMIN_PASSWORD = "ovulite2026"
ROLES = ["admin", "embryologist", "veterinarian", "researcher"]
MUTATING = {"POST", "PUT", "PATCH", "DELETE"}

# Mutating routes deliberately open to any caller, or to any signed-in role.
UNGATED_ALLOWED = {
    ("POST", "/auth/login"): "public: password login",
    ("POST", "/auth/refresh"): "public: exchanges a refresh token",
    ("POST", "/auth/register"): "public: self-signup, always pending approval",
    ("POST", "/auth/logout"): "caller ends their own session",
    ("POST", "/auth/logout-all"): "caller ends their own sessions",
    ("POST", "/auth/change-password"): "caller changes their own password",
    ("POST", "/auth/forgot-password"): "public: reset request, answer does not reveal accounts",
    ("POST", "/auth/reset-password"): "public: needs a single-use reset token",
    ("POST", "/auth/seed"): "bootstrap: refuses once any user exists, 404 in production",
    ("POST", "/auth/google"): "public: Google sign-in, verified server-side",
    ("POST", "/auth/google/mock"): "public demo sign-in, disabled in production",
    ("POST", "/literature/query"): "any signed-in role may ask the read-only literature assistant",
}


def _gate_roles(dependant):
    """The roles a route's require_role dependency allows, or None if it has no gate."""
    found = None
    stack = list(dependant.dependencies)
    while stack:
        dep = stack.pop()
        call = dep.call
        if getattr(call, "__name__", "") == "role_checker":
            cells = dict(zip(call.__code__.co_freevars, (c.cell_contents for c in call.__closure__)))
            found = set(cells["allowed"])
        stack.extend(dep.dependencies)
    return found


def _app_write_routes():
    """(method, path, gate) for every mutating route the app serves."""
    for router in app.routes:
        if type(router).__name__ != "_IncludedRouter":
            continue
        for candidate in router.effective_candidates():
            for method in sorted(candidate.methods & MUTATING):
                yield method, candidate.path, _gate_roles(candidate.dependant)


GATED = [(m, p, roles) for m, p, roles in _app_write_routes() if roles is not None]
UNGATED = {(m, p) for m, p, roles in _app_write_routes() if roles is None}


def _concrete(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "999999", path)


def _login(client, username: str, password: str = PASSWORD) -> dict:
    r = client.post("/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def _make_user(db_session, role: str, org_id: int) -> User:
    user = User(username=f"matrix_{role}_{uuid.uuid4().hex[:6]}", password_hash=hash_password(PASSWORD),
                role=role, active=True, organization_id=org_id)
    db_session.add(user)
    db_session.commit()
    return user


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# â”€â”€ RBAC â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@pytest.mark.integration
def test_route_introspection_finds_the_app_routes():
    # Guards the matrix itself: if route discovery breaks, the checks below pass
    # vacuously, so the count is asserted.
    assert len(GATED) >= 50, f"only {len(GATED)} gated write routes found"


@pytest.mark.integration
def test_every_ungated_write_is_deliberate():
    assert UNGATED == set(UNGATED_ALLOWED), (
        f"unexpected ungated writes: {sorted(UNGATED - set(UNGATED_ALLOWED))}; "
        f"allowlisted but not served: {sorted(set(UNGATED_ALLOWED) - UNGATED)}"
    )


@pytest.mark.integration
@pytest.mark.parametrize("role", ROLES)
def test_every_gated_write_refuses_roles_outside_its_gate(client, db_session, admin_user, admin_org_id, role):
    user = _make_user(db_session, role, admin_org_id)
    headers = _bearer(_login(client, user.username)["access_token"])
    failures = []
    for method, path, allowed in GATED:
        if role in allowed:
            continue
        r = client.request(method, _concrete(path), headers=headers, json={})
        if r.status_code != 403:
            failures.append(f"{method} {path} -> {r.status_code}")
    assert not failures, f"{role} got past a role gate:\n" + "\n".join(failures)


# â”€â”€ Token lifecycle â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@pytest.mark.integration
def test_expired_access_token_is_refused(client, admin_user, admin_org_id):
    token = create_access_token(
        {"sub": "admin", "role": "admin", "org_id": admin_org_id},
        expires_delta=timedelta(seconds=-60),
    )
    assert client.get("/auth/me", headers=_bearer(token)).status_code == 401


@pytest.mark.integration
def test_refresh_token_cannot_call_the_api(client, admin_user):
    refresh = _login(client, "admin", ADMIN_PASSWORD)["refresh_token"]
    assert client.get("/auth/me", headers=_bearer(refresh)).status_code == 401


@pytest.mark.integration
def test_access_token_cannot_be_used_to_refresh(client, admin_user):
    access = _login(client, "admin", ADMIN_PASSWORD)["access_token"]
    assert client.post("/auth/refresh", json={"refresh_token": access}).status_code == 401


@pytest.mark.integration
def test_forged_token_is_refused(client, admin_user, admin_org_id):
    forged = jwt.encode(
        {"sub": "admin", "role": "admin", "org_id": admin_org_id, "type": "access",
         "exp": 4102444800, "jti": str(uuid.uuid4())},
        "not-the-server-secret-but-long-enough-to-pass-length-rules", algorithm=ALGORITHM,
    )
    assert client.get("/auth/me", headers=_bearer(forged)).status_code == 401


@pytest.mark.integration
def test_role_is_read_from_the_database_not_the_token(client, db_session, admin_user, admin_org_id):
    user = _make_user(db_session, "researcher", admin_org_id)
    # A token that claims admin is still a researcher's token: the role is looked up.
    forged_admin = create_access_token(
        {"sub": user.username, "role": "admin", "org_id": admin_org_id, "user_id": user.user_id}
    )
    assert client.get("/admin/users", headers=_bearer(forged_admin)).status_code == 403


@pytest.mark.integration
def test_logout_ends_the_access_token_as_well(client, admin_user):
    tokens = _login(client, "admin", ADMIN_PASSWORD)
    headers = _bearer(tokens["access_token"])
    done = client.post("/auth/logout", headers=headers, json={"refresh_token": tokens["refresh_token"]})
    assert done.status_code == 200, done.text
    assert client.get("/auth/me", headers=headers).status_code == 401


@pytest.mark.integration
def test_disabled_account_loses_access_and_cannot_refresh(client, db_session, admin_user, admin_org_id):
    user = _make_user(db_session, "researcher", admin_org_id)
    tokens = _login(client, user.username)
    headers = _bearer(tokens["access_token"])
    assert client.get("/auth/me", headers=headers).status_code == 200

    admin_headers = _bearer(_login(client, "admin", ADMIN_PASSWORD)["access_token"])
    disabled = client.put(f"/admin/users/{user.user_id}", headers=admin_headers, json={"active": False})
    assert disabled.status_code == 200, disabled.text

    assert client.get("/auth/me", headers=headers).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
    refused = client.post("/auth/login", data={"username": user.username, "password": PASSWORD})
    assert refused.status_code == 403, refused.text


# â”€â”€ Bootstrap admin â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@pytest.mark.integration
def test_bootstrap_admin_needs_a_configured_password(db_session, monkeypatch):
    db_session.query(User).delete()
    monkeypatch.setattr(auth_api, "DEFAULT_ADMIN_PASSWORD", None)
    assert auth_api.ensure_default_admin(db_session) is False
    assert db_session.query(User).count() == 0


@pytest.mark.integration
def test_bootstrap_admin_is_created_from_the_configured_password(db_session, monkeypatch):
    db_session.query(User).delete()
    monkeypatch.setattr(auth_api, "DEFAULT_ADMIN_PASSWORD", "Provisioned!Pass1")
    assert auth_api.ensure_default_admin(db_session) is True
    admin = db_session.query(User).filter(User.username == "admin").one()
    assert auth_api.verify_password("Provisioned!Pass1", admin.password_hash)


@pytest.mark.integration
def test_seed_endpoint_is_not_served_in_production(client, monkeypatch):
    monkeypatch.setattr(auth_api, "IS_PRODUCTION", True)
    assert client.post("/auth/seed").status_code == 404


# â”€â”€ Organization isolation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def _outsider_headers(client, db_session) -> dict:
    """An admin of a different organization, who must not see the caller's records."""
    suffix = uuid.uuid4().hex[:6]
    org = Organization(name=f"Isolation {suffix}", slug=f"isolation-{suffix}")
    db_session.add(org)
    db_session.flush()
    user = _make_user(db_session, "admin", org.organization_id)
    return _bearer(_login(client, user.username)["access_token"])


ISOLATED = [
    ("donor", "/donors/", {"tag_id": "ISO-DONOR", "breed": "Holstein"}, "donor_id"),
    ("embryo", "/embryos/", {"stage": 7}, "embryo_id"),
    ("recipient", "/recipients/",
     {"tag_id": "ISO-RECIP", "farm_location": "Iso Farm", "cow_or_heifer": "Cow"}, "recipient_id"),
]


@pytest.mark.integration
@pytest.mark.parametrize("kind, base, payload, key", ISOLATED, ids=[k[0] for k in ISOLATED])
def test_another_organization_cannot_read_or_change_a_record(
    client, db_session, admin_user, auth_headers, kind, base, payload, key
):
    created = client.post(base, json=payload, headers=auth_headers)
    assert created.status_code == 201, created.text
    record_id = created.json()[key]
    outsider = _outsider_headers(client, db_session)

    assert client.get(f"{base}{record_id}", headers=outsider).status_code == 404
    assert client.put(f"{base}{record_id}", json={"notes": "changed"}, headers=outsider).status_code == 404
    assert client.delete(f"{base}{record_id}", headers=outsider).status_code == 404

    listed = client.get(base, params={"page_size": 100}, headers=outsider).json()["items"]
    assert record_id not in [item[key] for item in listed]

    owner_view = client.get(f"{base}{record_id}", headers=auth_headers)
    assert owner_view.status_code == 200
    assert owner_view.json().get("notes") != "changed"
