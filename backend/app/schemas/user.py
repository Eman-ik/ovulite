"""User-related Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.auth.password_policy import validate_password_strength


class UserCreate(BaseModel):
    """Schema for creating a new user (public signup).

    ``role`` and ``organization_id`` are accepted but IGNORED by
    /auth/register — it always creates the lowest-privilege role in the
    default organization. They are kept only so older clients that still send
    them get a 201 rather than a validation error; the router logs a warning
    when a role was asked for.
    """

    username: str
    password: str
    role: str = "researcher"
    organization_id: Optional[int] = None
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None

    @field_validator("password")
    @classmethod
    def password_must_be_strong(cls, v: str) -> str:
        return validate_password_strength(v)


class UserResponse(BaseModel):
    """Public user data returned by the API (never includes password_hash)."""

    user_id: int
    organization_id: Optional[int] = None
    username: str
    role: Optional[str]
    full_name: Optional[str]
    email: Optional[str]
    active: bool
    created_at: datetime
    # Reported so the frontend can send the user straight to the change-password
    # screen, rather than letting them click into the app and collect a 403
    # from every request.
    must_change_password: bool = False

    model_config = {"from_attributes": True}


class UserInDB(UserResponse):
    """Internal schema that includes the password hash (never returned to client)."""

    password_hash: str
