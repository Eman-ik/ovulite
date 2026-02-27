"""Pydantic schemas for Technician CRUD operations."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TechnicianBase(BaseModel):
    name: str
    role: Optional[str] = "ET Technician"
    active: bool = True


class TechnicianCreate(TechnicianBase):
    pass


class TechnicianUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    active: Optional[bool] = None


class TechnicianResponse(TechnicianBase):
    technician_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
