"""Schemas for administrative user management."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.auth.dependencies import CANONICAL_ROLES

MIN_PASSWORD_LENGTH = 10


def _validate_role(value: Optional[str]) -> Optional[str]:
    if value is not None and value not in CANONICAL_ROLES:
        raise ValueError(f"role must be one of {', '.join(CANONICAL_ROLES)}")
    return value


def _validate_password(value: str) -> str:
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    return value


class AdminUserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str
    role: str
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    active: bool = True

    _role = field_validator("role")(lambda cls, v: _validate_role(v))
    _password = field_validator("password")(lambda cls, v: _validate_password(v))


class AdminUserUpdate(BaseModel):
    """Password is deliberately absent — it has its own endpoint.

    Bundling a password reset into a general update makes it impossible to audit
    "who changed whose password" separately from "who renamed whom".
    """

    role: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    active: Optional[bool] = None

    _role = field_validator("role")(lambda cls, v: _validate_role(v))


class AdminPasswordReset(BaseModel):
    new_password: str
    _password = field_validator("new_password")(lambda cls, v: _validate_password(v))


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str
    role: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[str] = None
    active: bool
    organization_id: Optional[int] = None
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None


class RoleDescriptor(BaseModel):
    """A role plus what it can actually do, so the picker is not a bare list."""

    role: str
    label: str
    description: str
    can_write_lab: bool
    can_write_et: bool
    can_run_predictions: bool
    is_admin: bool
