"""Authentication request/response schemas."""

from pydantic import BaseModel, field_validator

from app.auth.password_policy import validate_password_strength


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
    # True for temporary passwords: every other endpoint refuses this user
    # until they call /auth/change-password.
    must_change_password: bool = False


class RefreshTokenRequest(BaseModel):
    """Request body for token refresh."""

    refresh_token: str


class GoogleAuthRequest(BaseModel):
    """Request body for Google Sign-In — the ID token from Google Identity Services."""

    token: str


class ChangePasswordRequest(BaseModel):
    """Body for POST /auth/change-password."""

    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_must_be_strong(cls, v: str) -> str:
        return validate_password_strength(v)


class ForgotPasswordRequest(BaseModel):
    """Request body for POST /auth/forgot-password."""

    email: str


class ForgotPasswordResponse(BaseModel):
    """Response for POST /auth/forgot-password.

    Always the same generic message whether or not the email exists, so this
    cannot be used to discover which addresses are registered. ``reset_token``
    is filled only outside production when no mail server is configured, so
    the flow can be exercised without SMTP.
    """

    message: str
    reset_token: str | None = None


class ResetPasswordRequest(BaseModel):
    """Request body for POST /auth/reset-password."""

    reset_token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_must_be_strong(cls, v: str) -> str:
        return validate_password_strength(v)


class LogoutRequest(BaseModel):
    """Optional body for POST /auth/logout.

    Send the refresh token so it is revoked alongside the access token;
    otherwise it stays usable until it expires on its own.
    """

    refresh_token: str | None = None


class LogoutResponse(BaseModel):
    message: str
    revoked_tokens: int


class RegisterResponse(BaseModel):
    """Reply to POST /auth/register.

    Deliberately not a UserResponse: signup is unauthenticated, and echoing
    the stored row back told the caller what role and organization they had
    been given. It also never confirms a role the caller asked for.
    """

    message: str
    username: str
    pending_approval: bool
