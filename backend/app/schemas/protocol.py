"""Pydantic schemas for Protocol CRUD operations."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ProtocolBase(BaseModel):
    name: str
    description: Optional[str] = None


class ProtocolCreate(ProtocolBase):
    pass


class ProtocolUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ProtocolResponse(ProtocolBase):
    protocol_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
