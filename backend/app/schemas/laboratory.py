"""Schemas for the Laboratory (site) entity."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.laboratory import SITE_TYPES


class LaboratoryBase(BaseModel):
    name: str
    code: Optional[str] = None
    site_type: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    active: bool = True
    notes: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        cleaned = (v or "").strip()
        if not cleaned:
            raise ValueError("Laboratory name cannot be blank")
        # Trimmed on the way in, because the free-text column this replaces
        # accumulated " DZF" and "DZF " as separate sites.
        return cleaned

    @field_validator("site_type")
    @classmethod
    def known_site_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in SITE_TYPES:
            raise ValueError(f"site_type must be one of {', '.join(SITE_TYPES)}")
        return v


class LaboratoryCreate(LaboratoryBase):
    pass


class LaboratoryUpdate(BaseModel):
    """Every field optional, but each one that exists on the base must appear
    here too — a field missing from an Update schema is silently dropped on PUT.
    """

    name: Optional[str] = None
    code: Optional[str] = None
    site_type: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    active: Optional[bool] = None
    notes: Optional[str] = None

    _name_not_blank = field_validator("name")(
        lambda cls, v: v if v is None else LaboratoryBase.name_not_blank(v)
    )
    _known_site_type = field_validator("site_type")(
        lambda cls, v: LaboratoryBase.known_site_type(v)
    )


class LaboratoryResponse(LaboratoryBase):
    model_config = ConfigDict(from_attributes=True)

    laboratory_id: int
    organization_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class LaboratoryUsage(BaseModel):
    """How many records point at a site.

    Shown before deactivation so the operator knows what they are hiding, and
    used to refuse a hard delete on a site with history.
    """

    laboratory_id: int
    name: str
    transfers: int
    opu_sessions: int
    recipients: int
