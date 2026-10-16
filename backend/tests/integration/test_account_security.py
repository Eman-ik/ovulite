"""Integration tests for the account-security hardening.

The first test is the regression guard for a real privilege escalation that
existed in this repository: POST /auth/register took `role` from the request
body, so an unauthenticated caller could create an admin for themselves.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.auth.security import MAX_FAILED_LOGIN_ATTEMPTS
from app.models.user import User

GOOD_PASSWORD = "Str0ng!Passw0rd"
OTHER_PASSWORD = "An0ther!Passw0rd"


def _signup(client, username="newbie", password=GOOD_PASSWORD, **extra):
    body = {"username": username, "password": password, "email": f"{username}@example.com"}
    body.update(extra)
    return client.post("/auth/register", json=body)


def _admin_headers(client, admin_user):
    r = client.post("/auth/login", data={"username": "admin", "password": "ovulite2026"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ── The escalation hole ────────────────────────────────────────────────────


@pytest.mark.integration
def test_signup_cannot_choose_its_own_role(client, db_session):
    """An unauthenticated signup asking for "admin" must not get it.

    This is the regression guard. Before the fix this returned 201 with
    role "admin", and that account could then call admin-gated endpoints.
    """
    response = _signup(client, "mallory", role="admin")
    assert response.status_code == 201, response.text
    # The response no longer echoes the stored row back to an anonymous caller.
    assert "role" not in response.json()

    created = db_session.query(User).filter(User.username == "mallory").first()
    assert created is not None
    assert created.role == "researcher", f"signup was granted role {created.role!r}"


@pytest.mark.integration
def test_signup_cannot_join_another_organization(client):
    response = _signup(client, "wanderer", organization_id=99999)
    assert response.status_code == 403, response.text


@pytest.mark.integration
def test_signup_is_pending_and_cannot_log_in(client):
    response = _signup(client, "pending_pat")
    assert response.status_code == 201, response.text
    assert response.json()["pending_approval"] is True

    denied = client.post("/auth/login", data={"username": "pending_pat", "password": GOOD_PASSWORD})
    assert denied.status_code == 403, denied.text
    assert "approve" in denied.json()["detail"].lower()


@pytest.mark.integration
def test_admin_approval_lets_the_account_in(client, db_session, admin_user):
    _signup(client, "approve_me")
    headers = _admin_headers(client, admin_user)
    target = db_session.query(User).filter(User.username == "approve_me").first()

    approved = client.post(f"/admin/users/{target.user_id}/approve", headers=headers)
    assert approved.status_code == 200, approved.text
    assert approved.json()["pending_approval"] is False
    assert approved.json()["approved_by"] == "admin"

    ok = client.post("/auth/login", data={"username": "approve_me", "password": GOOD_PASSWORD})
    assert ok.status_code == 200, ok.text

    # Approving twice is a conflict, not a silent no-op.
    again = client.post(f"/admin/users/{target.user_id}/approve", headers=headers)
    assert again.status_code == 409


@pytest.mark.integration
def test_password_policy_is_enforced_on_signup(client):
    weak = _signup(client, "weakling", password="password")
    assert weak.status_code == 422, weak.text


# ── Lockout ────────────────────────────────────────────────────────────────


@pytest.mark.integration
def test_account_locks_after_repeated_failures(client, admin_user):
    for _ in range(MAX_FAILED_LOGIN_ATTEMPTS):
        bad = client.post("/auth/login", data={"username": "admin", "password": "wrong"})
        assert bad.status_code == 401, bad.text

    # Locked now — and the CORRECT password must still be refused, otherwise
    # the lockout protects nothing.
    locked = client.post("/auth/login", data={"username": "admin", "password": "ovulite2026"})
    assert locked.status_code == 403, locked.text
    assert "locked" in locked.json()["detail"].lower()


@pytest.mark.integration
def test_admin_can_clear_a_lockout(client, db_session, admin_user):
    for _ in range(MAX_FAILED_LOGIN_ATTEMPTS):
        client.post("/auth/login", data={"username": "admin", "password": "wrong"})

    # Clear it directly: the only admin is the locked account itself here.
    target = db_session.query(User).filter(User.username == "admin").first()
    target.failed_login_count = 0
    target.locked_until = None
    db_session.commit()

    ok = client.post("/auth/login", data={"username": "admin", "password": "ovulite2026"})
    assert ok.status_code == 200, ok.text
    db_session.refresh(target)
    assert target.failed_login_count == 0, "a successful login must reset the counter"


# ── Password change ends other sessions ────────────────────────────────────


@pytest.mark.integration
def test_change_password_ends_other_sessions(client, admin_user):
    first = client.post("/auth/login", data={"username": "admin", "password": "ovulite2026"})
    old_headers = {"Authorization": f"Bearer {first.json()['access_token']}"}
    assert client.get("/auth/me", headers=old_headers).status_code == 200

    changed = client.post(
        "/auth/change-password",
        headers=old_headers,
        json={"current_password": "ovulite2026", "new_password": GOOD_PASSWORD},
    )
    assert changed.status_code == 200, changed.text

    # The token minted before the change is dead...
    assert client.get("/auth/me", headers=old_headers).status_code == 401
    # ...and the one handed back by the change still works.
    fresh = {"Authorization": f"Bearer {changed.json()['access_token']}"}
    assert client.get("/auth/me", headers=fresh).status_code == 200

    assert client.post("/auth/login", data={"username": "admin", "password": "ovulite2026"}).status_code == 401
    assert client.post("/auth/login", data={"username": "admin", "password": GOOD_PASSWORD}).status_code == 200


@pytest.mark.integration
def test_change_password_rejects_a_wrong_current_password(client, admin_user):
    headers = _admin_headers(client, admin_user)
    bad = client.post(
        "/auth/change-password",
        headers=headers,
        json={"current_password": "not-it", "new_password": GOOD_PASSWORD},
    )
    assert bad.status_code == 400, bad.text


@pytest.mark.integration
def test_logout_all_ends_the_current_session(client, admin_user):
    headers = _admin_headers(client, admin_user)
    assert client.post("/auth/logout-all", headers=headers).status_code == 200
    assert client.get("/auth/me", headers=headers).status_code == 401


# ── Forced password change ─────────────────────────────────────────────────


@pytest.mark.integration
def test_must_change_password_blocks_everything_else(client, db_session, admin_user):
    target = db_session.query(User).filter(User.username == "admin").first()
    target.must_change_password = True
    db_session.commit()

    login = client.post("/auth/login", data={"username": "admin", "password": "ovulite2026"})
    assert login.status_code == 200, login.text
    assert login.json()["must_change_password"] is True
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    blocked = client.get("/transfers/?page=1&page_size=5", headers=headers)
    assert blocked.status_code == 403
    assert blocked.json()["detail"] == "password_change_required"

    # /auth/me stays open so the frontend can explain itself.
    assert client.get("/auth/me", headers=headers).status_code == 200

    fixed = client.post(
        "/auth/change-password",
        headers=headers,
        json={"current_password": "ovulite2026", "new_password": GOOD_PASSWORD},
    )
    assert fixed.status_code == 200, fixed.text
    now = {"Authorization": f"Bearer {fixed.json()['access_token']}"}
    assert client.get("/transfers/?page=1&page_size=5", headers=now).status_code == 200


# ── Forgot / reset password ────────────────────────────────────────────────


@pytest.mark.integration
def test_forgot_password_does_not_reveal_whether_an_email_exists(client, db_session, admin_user):
    target = db_session.query(User).filter(User.username == "admin").first()
    target.email = "admin@example.com"
    db_session.commit()

    known = client.post("/auth/forgot-password", json={"email": "admin@example.com"})
    unknown = client.post("/auth/forgot-password", json={"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 200
    assert known.json()["message"] == unknown.json()["message"]
    # Only the real one carries a token (dev convenience, no mail server here).
    assert known.json()["reset_token"]
    assert unknown.json()["reset_token"] is None


@pytest.mark.integration
def test_reset_password_works_once_and_ends_sessions(client, db_session, admin_user):
    target = db_session.query(User).filter(User.username == "admin").first()
    target.email = "admin@example.com"
    db_session.commit()

    live = _admin_headers(client, admin_user)
    assert client.get("/auth/me", headers=live).status_code == 200

    token = client.post("/auth/forgot-password", json={"email": "admin@example.com"}).json()["reset_token"]
    done = client.post("/auth/reset-password", json={"reset_token": token, "new_password": OTHER_PASSWORD})
    assert done.status_code == 200, done.text

    # A reset exists because someone may hold the old credentials.
    assert client.get("/auth/me", headers=live).status_code == 401
    assert client.post("/auth/login", data={"username": "admin", "password": OTHER_PASSWORD}).status_code == 200

    # Single use.
    replay = client.post("/auth/reset-password", json={"reset_token": token, "new_password": GOOD_PASSWORD})
    assert replay.status_code == 400, replay.text


@pytest.mark.integration
def test_expired_reset_token_is_refused(client, db_session, admin_user):
    target = db_session.query(User).filter(User.username == "admin").first()
    target.email = "admin@example.com"
    db_session.commit()

    token = client.post("/auth/forgot-password", json={"email": "admin@example.com"}).json()["reset_token"]
    db_session.refresh(target)
    target.reset_token_expires = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    expired = client.post("/auth/reset-password", json={"reset_token": token, "new_password": OTHER_PASSWORD})
    assert expired.status_code == 400, expired.text


@pytest.mark.integration
def test_reset_token_is_not_stored_in_the_clear(client, db_session, admin_user):
    target = db_session.query(User).filter(User.username == "admin").first()
    target.email = "admin@example.com"
    db_session.commit()

    token = client.post("/auth/forgot-password", json={"email": "admin@example.com"}).json()["reset_token"]
    db_session.refresh(target)
    assert target.reset_token != token, "the raw reset token was stored"
    assert len(target.reset_token) == 64, "expected a SHA-256 hex digest"


# ── Refresh rotation ───────────────────────────────────────────────────────


@pytest.mark.integration
def test_refresh_tokens_rotate_and_replay_is_refused(client, admin_user):
    login = client.post("/auth/login", data={"username": "admin", "password": "ovulite2026"})
    first_refresh = login.json()["refresh_token"]

    rotated = client.post("/auth/refresh", json={"refresh_token": first_refresh})
    assert rotated.status_code == 200, rotated.text
    assert rotated.json()["refresh_token"] != first_refresh

    replay = client.post("/auth/refresh", json={"refresh_token": first_refresh})
    assert replay.status_code == 401, replay.text

    # The rotated one is still good.
    assert client.post(
        "/auth/refresh", json={"refresh_token": rotated.json()["refresh_token"]}
    ).status_code == 200


@pytest.mark.integration
def test_logout_revokes_the_refresh_token_too(client, admin_user):
    login = client.post("/auth/login", data={"username": "admin", "password": "ovulite2026"})
    tokens = login.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    out = client.post("/auth/logout", headers=headers, json={"refresh_token": tokens["refresh_token"]})
    assert out.status_code == 200, out.text
    assert out.json()["revoked_tokens"] == 2

    # The refresh token must not still mint new access tokens after logout.
    assert client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
