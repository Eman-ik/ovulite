"""
Integration tests for authentication API endpoints.

Tests:
- CT-1: Admin seed endpoint
- CT-2: Login returns token - CT-3: 401 without token
- CT-4: 200 with valid token
"""
import pytest
from fastapi import status


@pytest.mark.integration
class TestAdminSeedEndpoint:
    """Test admin user seed endpoint - CT-1"""

    def test_seed_admin_endpoint_creates_user(self, client, db_session):
        """CT-1: Test that /auth/seed creates admin user successfully"""
        response = client.post("/auth/seed")
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        assert "user_id" in data
        assert data["username"] == "admin"
        assert data["role"] == "admin"
        assert data["active"] is True

    def test_seed_admin_returns_409_if_users_exist(self, client, admin_user):
        """Test that seed endpoint returns 409 if users already exist"""
        # admin_user fixture already created a user
        response = client.post("/auth/seed")
        
        assert response.status_code == status.HTTP_409_CONFLICT


@pytest.mark.integration
class TestLoginEndpoint:
    """Test login endpoint - CT-2"""

    def test_login_returns_token_for_valid_credentials(self, client, admin_user):
        """CT-2: Test that login with correct credentials returns JWT token"""
        response = client.post(
            "/auth/login",
            data={"username": "admin", "password": "ovulite2026"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0

    def test_login_returns_401_for_invalid_username(self, client, admin_user):
        """Test that login with invalid username returns 401"""
        response = client.post(
            "/auth/login",
            data={"username": "nonexistent", "password": "any_password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "invalid username or password" in response.json()["detail"].lower()

    def test_login_returns_401_for_invalid_password(self, client, admin_user):
        """Test that login with invalid password returns 401"""
        response = client.post(
            "/auth/login",
            data={"username": "admin", "password": "wrong_password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "invalid username or password" in response.json()["detail"].lower()


@pytest.mark.integration
class TestProtectedEndpoints:
    """Test protected endpoint access control - CT-3, CT-4"""

    def test_protected_endpoint_returns_401_without_token(self, client):
        """CT-3: Test that protected endpoints reject requests without token"""
        response = client.get("/auth/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "detail" in response.json()

    def test_protected_endpoint_returns_401_with_invalid_token(self, client):
        """Test that protected endpoints reject requests with invalid token"""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid_token_xyz"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_protected_endpoint_returns_200_with_valid_token(self, client, admin_user, auth_headers):
        """CT-4: Test that protected endpoints accept requests with valid token"""
        response = client.get("/auth/me", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["username"] == "admin"
        assert data["role"] == "admin"
        assert "user_id" in data

    def test_me_endpoint_returns_current_user_profile(self, client, admin_user, auth_headers):
        """Test that /auth/me returns full user profile"""
        response = client.get("/auth/me", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify all expected fields
        assert "user_id" in data
        assert "username" in data
        assert "role" in data
        assert "active" in data
        assert "full_name" in data
        # Password hash should NOT be in response
        assert "password" not in data
        assert "password_hash" not in data
