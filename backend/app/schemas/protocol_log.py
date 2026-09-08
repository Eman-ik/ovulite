"""Pydantic schemas for Protocol Log CRUD operations.

A protocol log entry records one step of a synchronization protocol
(e.g. a CIDR insertion, a GnRH injection) actually administered for a
given ET transfer — distinct from the Protocol template itself.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class ProtocolLogBase(BaseModel):
    transfer_id: Optional[int] = None
    protocol_id: Optional[int] = None
    step_name: Optional[str] = None
    step_date: Optional[date] = None
    drug_name: Optional[str] = None
    dosage: Optional[str] = None
    notes: Optional[str] = None


class ProtocolLogCreate(ProtocolLogBase):
    pass


class ProtocolLogUpdate(BaseModel):
    transfer_id: Optional[int] = None
    protocol_id: Optional[int] = None
    step_name: Optional[str] = None
    step_date: Optional[date] = None
    drug_name: Optional[str] = None
    dosage: Optional[str] = None
    notes: Optional[str] = None


class ProtocolLogResponse(ProtocolLogBase):
    log_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
