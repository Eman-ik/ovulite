"""Pydantic schemas for Donor CRUD operations."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class DonorBase(BaseModel):
    tag_id: str
    breed: Optional[str] = None
    birth_weight_epd: Optional[Decimal] = None
    notes: Optional[str] = None


class DonorCreate(DonorBase):
    pass


class DonorUpdate(BaseModel):
    tag_id: Optional[str] = None
    breed: Optional[str] = None
    birth_weight_epd: Optional[Decimal] = None
    notes: Optional[str] = None


class DonorResponse(DonorBase):
    donor_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
