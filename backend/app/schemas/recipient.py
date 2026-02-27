"""Pydantic schemas for Recipient CRUD operations."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RecipientBase(BaseModel):
    tag_id: str
    farm_location: Optional[str] = None
    cow_or_heifer: Optional[str] = None
    notes: Optional[str] = None


class RecipientCreate(RecipientBase):
    pass


class RecipientUpdate(BaseModel):
    tag_id: Optional[str] = None
    farm_location: Optional[str] = None
    cow_or_heifer: Optional[str] = None
    notes: Optional[str] = None


class RecipientResponse(RecipientBase):
    recipient_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
