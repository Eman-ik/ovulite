"""Google sign-in provisions accounts. They must use a role the database accepts;
the constraint no longer lists 'viewer', so provisioning with it failed."""

import pytest

from app.models.user import User


@pytest.mark.integration
def test_google_demo_login_provisions_a_researcher(client, db_session, admin_user):
    r = client.post("/auth/google/mock")
    assert r.status_code == 200, r.text
    user = db_session.query(User).filter(User.username == "google_demo").first()
    assert user is not None
    assert user.role == "researcher"
