"""Mapped ET intake independent of positional legacy imports and ML datasets."""
import csv
import io
from collections import Counter
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


class CanonicalET(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, allow_inf_nan=False, extra="forbid")
    et_number: int = Field(gt=0)
    et_date: date
    recipient_tag: str = Field(min_length=1, max_length=50)
    farm_location: str = Field(min_length=1, max_length=200)
    donor_tag: str | None = Field(default=None, max_length=50)
    sire_name: str | None = Field(default=None, max_length=100)
    embryo_stage: int = Field(ge=4, le=8)
    embryo_grade: int = Field(ge=1, le=4)
    fresh_or_frozen: Literal["Fresh", "Frozen"] | None = None
    bc_score: float | None = Field(default=None, ge=1, le=5)
    cl_measure_mm: float | None = Field(default=None, ge=0, le=50)
    cl_side: Literal["Left", "Right"] | None = None
    pc1_date: date | None = None
    pc1_result: Literal["Pregnant", "Open", "Recheck"] | None = None
    recipient_breed: str | None = Field(default=None, max_length=100)
    recipient_age_years: float | None = Field(default=None, ge=0)
    recipient_parity: int | None = Field(default=None, ge=0)
    cow_or_heifer: Literal["Cow", "Heifer"] | None = None
    previous_et_count: int | None = Field(default=None, ge=0)
    previous_et_pregnancies: int | None = Field(default=None, ge=0)
    previous_et_failures: int | None = Field(default=None, ge=0)
    prior_pregnancy_loss: bool | None = None
    donor_breed: str | None = Field(default=None, max_length=100)
    donor_age_years: float | None = Field(default=None, ge=0)
    donor_parity: int | None = Field(default=None, ge=0)
    donor_bcs: float | None = Field(default=None, ge=1, le=5)
    sire_breed: str | None = Field(default=None, max_length=100)
    semen_type: Literal["Conventional", "Sexed", "Unknown"] | None = None
    semen_batch: str | None = Field(default=None, max_length=100)
    embryo_identifier: str | None = Field(default=None, max_length=100)
    embryo_day: int | None = Field(default=None, ge=1)
    production_method: Literal["IVF", "MOET", "Other"] | None = None
    cryopreservation_method: str | None = Field(default=None, max_length=100)
    freezing_date: date | None = None
    opu_date: date | None = None
    ivf_date: date | None = None
    culture_media: str | None = Field(default=None, max_length=100)
    protocol_name: str | None = Field(default=None, max_length=100)
    technician_name: str | None = Field(default=None, max_length=100)
    p4_ng_ml: float | None = Field(default=None, ge=0)
    cl_quality: str | None = Field(default=None, max_length=100)
    estrus_date: date | None = None
    estrus_type: str | None = Field(default=None, max_length=100)
    days_estrus_to_et: float | None = Field(default=None, ge=0)
    heat_observed: bool | None = None
    transfer_side: Literal["Left", "Right"] | None = None
    transfer_location: str | None = Field(default=None, max_length=100)
    transfer_difficulty: str | None = Field(default=None, max_length=100)
    season: str | None = Field(default=None, max_length=50)
    ambient_temperature_c: float | None = Field(default=None, ge=-50, le=60)
    relative_humidity_pct: float | None = Field(default=None, ge=0, le=100)
    pc2_date: date | None = None
    pc2_result: Literal["Pregnant", "Open", "Recheck"] | None = None
    pregnancy_loss: bool | None = None
    pregnancy_loss_date: date | None = None
    calving_date: date | None = None
    calving_outcome: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("fresh_or_frozen", "cl_side", "transfer_side", "cow_or_heifer", "semen_type", "pc1_result", "pc2_result", mode="before")
    @classmethod
    def normalize(cls, value):
        if value is None:
            return None
        value = str(value).strip().lower()
        return {"p": "Pregnant", "positive": "Pregnant", "o": "Open", "negative": "Open", "pending": "Recheck"}.get(value, value.title())

    @model_validator(mode="after")
    def checkpoint(self):
        if self.pc1_date and self.pc1_date < self.et_date:
            raise ValueError("Pregnancy check date must not precede ET date")
        if self.pc1_result in {"Pregnant", "Open"} and not self.pc1_date:
            raise ValueError("A resolved pregnancy outcome requires a checkpoint date")
        if self.pc2_result in {"Pregnant", "Open"} and not self.pc2_date:
            raise ValueError("A resolved second pregnancy outcome requires a checkpoint date")
        if self.pc2_date and self.pc2_date < (self.pc1_date or self.et_date):
            raise ValueError("Second pregnancy check cannot precede first check or transfer")
        for name in ("opu_date", "ivf_date", "freezing_date", "estrus_date"):
            value = getattr(self, name)
            if value and value > self.et_date:
                raise ValueError(f"{name} cannot follow the transfer date")
        if self.opu_date and self.ivf_date and self.ivf_date < self.opu_date:
            raise ValueError("IVF date cannot precede OPU date")
        if self.freezing_date and self.ivf_date and self.freezing_date < self.ivf_date:
            raise ValueError("Freezing date cannot precede IVF date")
        if self.days_estrus_to_et is not None and self.estrus_date and self.days_estrus_to_et != (self.et_date - self.estrus_date).days:
            raise ValueError("Estrus-to-ET interval disagrees with the supplied dates")
        if self.previous_et_count is not None:
            if (self.previous_et_pregnancies or 0) + (self.previous_et_failures or 0) > self.previous_et_count:
                raise ValueError("Previous ET pregnancies and failures exceed the previous ET count")
        for name in ("pregnancy_loss_date", "calving_date"):
            value = getattr(self, name)
            if value and value < self.et_date:
                raise ValueError(f"{name} cannot precede transfer")
        if self.pregnancy_loss_date and self.pregnancy_loss is not True:
            raise ValueError("A loss date requires pregnancy_loss=true")
        return self


def read_csv(text):
    if len(text.encode("utf-8")) > 5000000:
        raise ValueError("CSV exceeds the 5 MB UTF-8 limit")
    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")), dialect=dialect)
    headers = reader.fieldnames or []
    if not headers or len(headers) != len(set(headers)) or any(not h.strip() for h in headers):
        raise ValueError("CSV must have non-empty, unique column names")
    rows = list(reader)
    if not rows or len(rows) > 10000:
        raise ValueError("Upload between 1 and 10,000 rows per batch")
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError("Each CSV row must contain the same number of cells as the header")
    return headers, rows


def validate_csv(text: str, mapping: dict, existing: set[int], existing_embryos: set[str] | None = None):
    headers, rows = read_csv(text)
    unknown = set(mapping) - set(CanonicalET.model_fields)
    if unknown or any(source not in headers for source in mapping.values()):
        raise ValueError("Mapping contains an unknown field or source column")
    if len(set(mapping.values())) != len(mapping):
        raise ValueError("Map each source column only once")
    required = {key for key, field in CanonicalET.model_fields.items() if field.is_required()}
    if not required <= mapping.keys():
        raise ValueError("Map required fields: " + ", ".join(sorted(required - mapping.keys())))
    values, results = [], []
    incomplete = 0
    for index, row in enumerate(rows, 2):
        mapped = {key: row[source].strip() or None for key, source in mapping.items()}
        incomplete += any(mapped.get(key) is None for key in required)
        try:
            value = CanonicalET.model_validate(mapped)
            values.append((index, value))
        except ValidationError as error:
            results.append({"row": index, "status": "rejected", "errors": [f"{'.'.join(map(str, e['loc'])) or 'record'}: {e['msg']}" for e in error.errors()]})
    counts = Counter(value.et_number for _, value in values)
    embryo_counts = Counter(value.embryo_identifier for _, value in values if value.embryo_identifier)
    accepted = []
    for index, value in values:
        duplicate = value.et_number in existing or counts[value.et_number] > 1 or (value.embryo_identifier and (value.embryo_identifier in (existing_embryos or set()) or embryo_counts[value.embryo_identifier] > 1))
        results.append({"row": index, "status": "duplicate" if duplicate else "accepted", "errors": ["ET number or external embryo identifier already exists in this organization or repeats in this file"] if duplicate else []})
        if not duplicate:
            accepted.append((index, value))
    summary = Counter(result["status"] for result in results)
    return accepted, {"schema_version": "2.0", "total": len(rows), "accepted": summary["accepted"], "rejected": summary["rejected"], "duplicate": summary["duplicate"],
                      "missing_by_field": {key: sum(not row.get(mapping.get(key), "").strip() for row in rows) for key in CanonicalET.model_fields},
                      "unmapped_columns": [header for header in headers if header not in mapping.values()],
                      "incomplete": incomplete,
                      "rows": sorted(results, key=lambda result: result["row"])}
