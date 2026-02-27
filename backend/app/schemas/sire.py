"""Pydantic schemas for Sire CRUD operations."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class SireBase(BaseModel):
    name: str
    breed: Optional[str] = None
    birth_weight_epd: Optional[Decimal] = None
    semen_type: Optional[str] = None
    notes: Optional[str] = None


class SireCreate(SireBase):
    pass


class SireUpdate(BaseModel):
    name: Optional[str] = None
    breed: Optional[str] = None
    birth_weight_epd: Optional[Decimal] = None
    semen_type: Optional[str] = None
    notes: Optional[str] = None


class SireResponse(SireBase):
    sire_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
