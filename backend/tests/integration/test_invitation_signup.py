"""Joining an organization needs an invitation the organization's admin issued.

Without email, the code is the only proof that a signup was invited. These tests
pin the rules that make it one: required, unexpired, single-use, bound to the
email it was issued for, and it decides the organization.
"""

from datetime import timedelta

import pytest

from app.models.organization import Organization
from app.models.user import User

PASSWORD = "Str0ng!Passw0rd"


def _signup(client, username, email, invitation_code=None):
    body = {"username": username, "password": PASSWORD, "email": email}
    if invitation_code is not None:
        body["invitation_code"] = invitation_code
    return client.post("/auth/register", json=body)


@pytest.mark.integration
def test_signup_without_a_code_is_refused(client):
    response = _signup(client, "no_code", "no_code@example.com")
    assert response.status_code == 400, response.text
    assert "invitation code" in response.json()["detail"].lower()


@pytest.mark.integration
def test_unknown_code_is_refused(client):
    response = _signup(client, "guesser", "guesser@example.com", invitation_code="not-a-real-code")
    assert response.status_code == 400, response.text


@pytest.mark.integration
def test_expired_code_is_refused(client, issue_invitation):
    code = issue_invitation("late@example.com", expires_in=timedelta(days=-1))
    response = _signup(client, "late", "late@example.com", invitation_code=code)
    assert response.status_code == 400, response.text


@pytest.mark.integration
def test_spent_code_is_refused(client, issue_invitation):
    code = issue_invitation("spent@example.com", status="accepted")
    response = _signup(client, "spent", "spent@example.com", invitation_code=code)
    assert response.status_code == 400, response.text


@pytest.mark.integration
def test_code_issued_to_another_email_is_refused(client, issue_invitation):
    code = issue_invitation("intended@example.com")
    response = _signup(client, "impostor", "impostor@example.com", invitation_code=code)
    assert response.status_code == 400, response.text
    assert "different email" in response.json()["detail"].lower()


@pytest.mark.integration
def test_email_match_ignores_case(client, issue_invitation):
    code = issue_invitation("Mixed.Case@Example.com")
    response = _signup(client, "casey", "mixed.case@example.com", invitation_code=code)
    assert response.status_code == 201, response.text


@pytest.mark.integration
def test_a_code_works_once(client, issue_invitation):
    code = issue_invitation("once@example.com")
    first = _signup(client, "once_first", "once@example.com", invitation_code=code)
    assert first.status_code == 201, first.text

    # Retrying with the same email would hit the email-in-use check first, so use a
    # different one: the only reason left to refuse is that the code is spent.
    second = _signup(client, "once_second", "once_retry@example.com", invitation_code=code)
    assert second.status_code == 400, second.text
    assert "invalid or has expired" in second.json()["detail"]


@pytest.mark.integration
def test_code_places_the_account_in_its_organization(client, db_session, issue_invitation):
    other = Organization(name="Second Lab", slug="second-lab")
    db_session.add(other)
    db_session.commit()
    code = issue_invitation("second@example.com", org_id=other.organization_id)

    response = _signup(client, "second_lab_user", "second@example.com", invitation_code=code)
    assert response.status_code == 201, response.text
    user = db_session.query(User).filter(User.username == "second_lab_user").one()
    assert user.organization_id == other.organization_id
    assert user.pending_approval is True


@pytest.mark.integration
def test_open_organization_registration_is_gone(client):
    response = client.post(
        "/auth/register-organization",
        json={
            "organization": {"name": "Anyone Lab", "slug": "anyone-lab"},
            "admin_username": "anyone_admin",
            "admin_password": PASSWORD,
        },
    )
    assert response.status_code == 404, response.text
