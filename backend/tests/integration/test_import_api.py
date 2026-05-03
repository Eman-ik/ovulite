"""Integration tests for CSV import endpoint behavior and authorization."""

from __future__ import annotations

import io

import pytest

from app.auth.security import hash_password
from app.models.user import User


@pytest.mark.integration
def test_import_csv_rejects_non_csv_file_type(client, auth_headers):
    response = client.post(
        "/import/csv",
        files={"file": ("not_csv.txt", io.BytesIO(b"hello"), "text/plain")},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "csv" in response.text.lower()


@pytest.mark.integration
def test_import_csv_requires_auth(client):
    response = client.post(
        "/import/csv",
        files={"file": ("x.csv", io.BytesIO(b"a,b\n1,2\n"), "text/csv")},
    )
    assert response.status_code == 401


@pytest.mark.integration
def test_import_csv_forbidden_for_viewer_role(client, db_session):
    username = "viewer_user"
    password = "viewer-password"

    db_session.add(
        User(
            username=username,
            password_hash=hash_password(password),
            role="viewer",
            active=True,
        )
    )
    db_session.commit()

    login = client.post(
        "/auth/login",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    response = client.post(
        "/import/csv",
        files={"file": ("x.csv", io.BytesIO(b"a,b\n1,2\n"), "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
