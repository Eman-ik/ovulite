"""Integration tests for JWT refresh token mechanism."""

import pytest
from fastapi.testclient import TestClient


class TestAuthRefresh:
    """Test suite for refresh token functionality."""

    def test_login_returns_refresh_token(self, client: TestClient, admin_user):
        """Verify login returns both access and refresh tokens."""
        response = client.post(
            "/auth/login",
            data={"username": "admin", "password": "ovulite2026"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 1800  # 30 minutes

    def test_refresh_token_returns_new_access_token(self, client: TestClient, admin_user):
        """Verify refresh endpoint returns new access token."""
        # First login to get tokens
        login_response = client.post(
            "/auth/login",
            data={"username": "admin", "password": "ovulite2026"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        
        # Use refresh token to get new access token
        refresh_response = client.post(
            "/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        # Refresh token should be the same
        assert new_tokens["refresh_token"] == tokens["refresh_token"]
        
        # Verify the refreshed token works for protected endpoints
        me_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["username"] == "admin"

    def test_refresh_with_invalid_token_returns_401(self, client: TestClient):
        """Verify invalid refresh token returns 401."""
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "invalid_token_xyz"},
        )
        assert response.status_code == 401

    def test_refresh_with_access_token_returns_401(self, client: TestClient, admin_user):
        """Verify using access token instead of refresh token returns 401."""
        # Login to get tokens
        login_response = client.post(
            "/auth/login",
            data={"username": "admin", "password": "ovulite2026"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        tokens = login_response.json()
        
        # Try to use access token as refresh token (should fail)
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": tokens["access_token"]},
        )
        assert response.status_code == 401

    def test_new_access_token_works_for_protected_endpoints(
        self, client: TestClient, admin_user
    ):
        """Verify new access token from refresh can access protected endpoints."""
        # Login and refresh to get new access token
        login_response = client.post(
            "/auth/login",
            data={"username": "admin", "password": "ovulite2026"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        tokens = login_response.json()
        
        refresh_response = client.post(
            "/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        new_access_token = refresh_response.json()["access_token"]
        
        # Use new access token to call protected endpoint
        me_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {new_access_token}"},
        )
        assert me_response.status_code == 200
        assert me_response.json()["username"] == "admin"
