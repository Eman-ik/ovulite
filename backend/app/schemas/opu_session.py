"""Pydantic schemas for OPU Session CRUD operations."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, computed_field, model_validator


class OPUSessionBase(BaseModel):
    donor_id: int
    opu_date: date
    technician_id: Optional[int] = None
    farm_location: Optional[str] = None
    total_follicles: Optional[int] = None
    oocytes_recovered: Optional[int] = None
    viable_oocytes: Optional[int] = None
    grade_a_oocytes: Optional[int] = Field(default=None, ge=0, le=200)
    grade_b_oocytes: Optional[int] = Field(default=None, ge=0, le=200)
    grade_c_oocytes: Optional[int] = Field(default=None, ge=0, le=200)
    degenerated_oocytes: Optional[int] = Field(default=None, ge=0, le=200)
    oocyte_morphology_notes: Optional[str] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_oocyte_grades(self) -> "OPUSessionBase":
        """Graded oocytes cannot outnumber the oocytes recovered.

        Checked here rather than in the database because the grades are
        entered after recovery, often in a separate pass, and a partial tally
        is legitimate — only a tally that exceeds the total is an error.
        """
        graded = [
            self.grade_a_oocytes,
            self.grade_b_oocytes,
            self.grade_c_oocytes,
            self.degenerated_oocytes,
        ]
        if self.oocytes_recovered is not None and any(g is not None for g in graded):
            total = sum(g or 0 for g in graded)
            if total > self.oocytes_recovered:
                raise ValueError(
                    f"Graded oocytes ({total}) exceed oocytes recovered ({self.oocytes_recovered})"
                )
        return self

    @model_validator(mode="after")
    def validate_counts(self) -> "OPUSessionBase":
        if (
            self.total_follicles is not None
            and self.oocytes_recovered is not None
            and self.oocytes_recovered > self.total_follicles
        ):
            raise ValueError("oocytes_recovered cannot exceed total_follicles")
        if (
            self.oocytes_recovered is not None
            and self.viable_oocytes is not None
            and self.viable_oocytes > self.oocytes_recovered
        ):
            raise ValueError("viable_oocytes cannot exceed oocytes_recovered")
        return self


class OPUSessionCreate(OPUSessionBase):
    pass


class OPUSessionUpdate(BaseModel):
    donor_id: Optional[int] = None
    opu_date: Optional[date] = None
    technician_id: Optional[int] = None
    farm_location: Optional[str] = None
    total_follicles: Optional[int] = None
    oocytes_recovered: Optional[int] = None
    viable_oocytes: Optional[int] = None
    grade_a_oocytes: Optional[int] = Field(default=None, ge=0, le=200)
    grade_b_oocytes: Optional[int] = Field(default=None, ge=0, le=200)
    grade_c_oocytes: Optional[int] = Field(default=None, ge=0, le=200)
    degenerated_oocytes: Optional[int] = Field(default=None, ge=0, le=200)
    oocyte_morphology_notes: Optional[str] = None
    notes: Optional[str] = None


class OPUSessionResponse(OPUSessionBase):
    opu_id: int
    donor_tag: Optional[str] = None
    technician_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def recovery_rate(self) -> Optional[float]:
        """oocytes_recovered / total_follicles, as a fraction. None when either count is unknown."""
        if not self.total_follicles or self.oocytes_recovered is None:
            return None
        return round(self.oocytes_recovered / self.total_follicles, 4)
