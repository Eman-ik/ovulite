"""Pydantic schemas for ET Transfer CRUD operations."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ETTransferBase(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    et_number: Optional[int] = None
    lab: Optional[str] = None
    satellite: Optional[str] = None
    customer_id: Optional[str] = None
    et_date: date
    farm_location: Optional[str] = None
    # The site this record belongs to. ``farm_location`` above is the
    # imported free text, kept as the source record; new writes should
    # set this instead. See app/models/laboratory.py.
    laboratory_id: Optional[int] = None
    recipient_id: Optional[int] = None
    bc_score: Optional[Decimal] = Field(default=None, ge=1, le=5)
    cl_side: Optional[str] = None
    cl_measure_mm: Optional[Decimal] = None
    protocol_id: Optional[int] = None
    heat_observed: Optional[bool] = None
    heat_day: Optional[int] = None
    embryo_id: Optional[int] = None
    technician_id: Optional[int] = None
    assistant_name: Optional[str] = None
    pc1_date: Optional[date] = None
    pc1_result: Optional[str] = None
    pc2_date: Optional[date] = None
    pc2_result: Optional[str] = None
    fetal_sexing: Optional[str] = None
    days_in_pregnancy: Optional[int] = None

    @field_validator("cl_side")
    @classmethod
    def validate_cl_side(cls, v: str | None) -> str | None:
        if v is not None and v not in ("Left", "Right"):
            raise ValueError("CL side must be 'Left' or 'Right'")
        return v

    @field_validator("cl_measure_mm")
    @classmethod
    def validate_cl_measure(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and (v < 0 or v > 50):
            raise ValueError("CL measure must be between 0 and 50 mm")
        return v

    @field_validator("pc1_result")
    @classmethod
    def validate_pc1_result(cls, v: str | None) -> str | None:
        if v is not None and v not in ("Pregnant", "Open", "Recheck"):
            raise ValueError("PC1 result must be 'Pregnant', 'Open', or 'Recheck'")
        return v

    @model_validator(mode="after")
    def check_dates(self):
        if self.pc1_date and self.pc1_date < self.et_date:
            raise ValueError("First pregnancy check cannot precede transfer")
        if self.pc2_date and self.pc2_date < (self.pc1_date or self.et_date):
            raise ValueError("Second pregnancy check cannot precede transfer or first check")
        if self.pc2_result is not None and self.pc2_result not in {"Pregnant", "Open", "Recheck"}:
            raise ValueError("Second pregnancy result must be Pregnant, Open or Recheck")
        return self


class ETTransferCreate(ETTransferBase):
    pass


class ETTransferUpdate(BaseModel):
    et_number: Optional[int] = None
    lab: Optional[str] = None
    satellite: Optional[str] = None
    customer_id: Optional[str] = None
    et_date: Optional[date] = None
    farm_location: Optional[str] = None
    laboratory_id: Optional[int] = None
    recipient_id: Optional[int] = None
    bc_score: Optional[Decimal] = None
    cl_side: Optional[str] = None
    cl_measure_mm: Optional[Decimal] = None
    protocol_id: Optional[int] = None
    heat_observed: Optional[bool] = None
    heat_day: Optional[int] = None
    embryo_id: Optional[int] = None
    technician_id: Optional[int] = None
    assistant_name: Optional[str] = None
    pc1_date: Optional[date] = None
    pc1_result: Optional[str] = None
    pc2_date: Optional[date] = None
    pc2_result: Optional[str] = None
    fetal_sexing: Optional[str] = None
    days_in_pregnancy: Optional[int] = None


class ETTransferResponse(ETTransferBase):
    transfer_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ETTransferDetail(ETTransferResponse):
    """Extended response with joined entity names for table display."""
    donor_tag: Optional[str] = None
    donor_breed: Optional[str] = None
    sire_name: Optional[str] = None
    recipient_tag: Optional[str] = None
    technician_name: Optional[str] = None
    protocol_name: Optional[str] = None
    embryo_stage: Optional[int] = None
    embryo_grade: Optional[int] = None
    fresh_or_frozen: Optional[str] = None
