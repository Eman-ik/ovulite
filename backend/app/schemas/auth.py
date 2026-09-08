"""Authentication request/response schemas."""

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Login credentials submitted by the user."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """JWT token returned after successful authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800  # 30 minutes in seconds
    organization_id: int | None = None


class RefreshTokenRequest(BaseModel):
    """Request body for token refresh."""

    refresh_token: str


class GoogleAuthRequest(BaseModel):
    """Request body for Google Sign-In — the ID token from Google Identity Services."""

    token: str


