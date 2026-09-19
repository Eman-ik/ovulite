"""Pydantic schemas for Recipient CRUD operations."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class RecipientBase(BaseModel):
    tag_id: str
    farm_location: Optional[str] = None
    # The site this record belongs to. ``farm_location`` above is the
    # imported free text, kept as the source record; new writes should
    # set this instead. See app/models/laboratory.py.
    laboratory_id: Optional[int] = None
    cow_or_heifer: Optional[str] = None
    breed: Optional[str] = None
    birth_date: Optional[date] = None
    parity: Optional[int] = Field(default=None, ge=0, le=20)
    reproductive_status: Optional[str] = None
    reproductive_disorders: Optional[str] = None
    previous_ai_count: Optional[int] = Field(default=None, ge=0, le=50)
    previous_et_count: Optional[int] = Field(default=None, ge=0, le=50)
    notes: Optional[str] = None


class RecipientCreate(RecipientBase):
    pass


class RecipientUpdate(BaseModel):
    tag_id: Optional[str] = None
    farm_location: Optional[str] = None
    laboratory_id: Optional[int] = None
    cow_or_heifer: Optional[str] = None
    breed: Optional[str] = None
    birth_date: Optional[date] = None
    parity: Optional[int] = Field(default=None, ge=0, le=20)
    reproductive_status: Optional[str] = None
    reproductive_disorders: Optional[str] = None
    previous_ai_count: Optional[int] = Field(default=None, ge=0, le=50)
    previous_et_count: Optional[int] = Field(default=None, ge=0, le=50)
    notes: Optional[str] = None


class RecipientResponse(RecipientBase):
    recipient_id: int
    # Derived from birth_date on read, so it can never be a stale stored value.
    age_years: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
