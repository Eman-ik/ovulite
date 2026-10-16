import hashlib
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    ADMIN_ROLES,
    ET_WRITE_ROLES,
    LAB_WRITE_ROLES,
    require_role,
)
from app.database import get_db
from app.models.donor import Donor
from app.models.embryo import Embryo
from app.models.et_transfer import ETTransfer
from app.models.intake_batch import IntakeBatch, TransferProvenance
from app.models.organization import Organization
from app.models.recipient import Recipient
from app.models.sire import Sire
from app.models.user import User
from app.models.intake_governance import EmbryoIdentifier, IntakeRevision
from app.services.canonical_intake import CanonicalET, read_csv, validate_csv
from app.services.case_persistence import persist_case

router = APIRouter()
writer = require_role(*ADMIN_ROLES, *LAB_WRITE_ROLES, *ET_WRITE_ROLES)


class Preview(BaseModel):
    filename: str = Field(min_length=1, max_length=200)
    csv_text: str = Field(min_length=1, max_length=5000000)
    mapping: dict[str, str]
    source_type: Literal["real_internal", "external_collaboration", "public_dataset", "synthetic_demo"]
    source_reference: str = Field(min_length=5, max_length=1000)

    @field_validator("filename", "source_reference", mode="before")
    @classmethod
    def trim_metadata(cls, value):
        return value.strip() if isinstance(value, str) else value


class Inspect(BaseModel):
    csv_text: str = Field(min_length=1, max_length=5000000)


def org(user):
    if user.organization_id is None:
        raise HTTPException(403, "An organization is required")
    return user.organization_id


def revision(db, batch, user):
    db.flush()
    db.add(IntakeRevision(batch_id=batch.batch_id, organization_id=batch.organization_id, actor=user.username,
        state={"status": batch.status, "mapping": batch.mapping, "report": batch.report,
               "source_type": batch.source_type, "source_reference": batch.source_reference}))


def embryo_identifiers(db, organization_id):
    return {value for value, in db.query(EmbryoIdentifier.identifier).filter_by(organization_id=organization_id)}


@router.post("/inspect")
def inspect(payload: Inspect, user: User = Depends(writer)):
    org(user)
    try:
        headers, rows = read_csv(payload.csv_text)
    except ValueError as error:
        raise HTTPException(422, str(error))
    return {"headers": headers, "sample": rows[:3], "fields": CanonicalET.model_json_schema()["properties"],
            "required": [key for key, field in CanonicalET.model_fields.items() if field.is_required()]}


@router.post("/preview", status_code=201)
def preview(payload: Preview, db: Session = Depends(get_db), user: User = Depends(writer)):
    organization_id = org(user)
    if "new_records" in payload.filename.lower() and payload.source_type != "synthetic_demo":
        raise HTTPException(422, "New_Records sources are quarantined by existing project policy. They may only be retained as synthetic demonstration data.")
    existing = {number for number, in db.query(ETTransfer.et_number).filter_by(organization_id=organization_id)}
    try:
        _, report = validate_csv(payload.csv_text, payload.mapping, existing, embryo_identifiers(db, organization_id))
    except ValueError as error:
        raise HTTPException(422, str(error))
    checksum = hashlib.sha256(payload.csv_text.encode()).hexdigest()
    prior = db.query(IntakeBatch).filter_by(organization_id=organization_id, checksum=checksum).with_for_update().first()
    if prior:
        if prior.status != "preview":
            raise HTTPException(409, "This CSV has already been committed or staged")
        # A failed mapping can be corrected before commit; raw source stays unchanged.
        prior.mapping = payload.mapping
        prior.report = report
        prior.source_type = payload.source_type
        prior.source_reference = payload.source_reference
        revision(db, prior, user)
        db.commit()
        return {"batch_id": prior.batch_id, "report": report, "source_type": prior.source_type}
    batch = IntakeBatch(batch_id=str(uuid.uuid4()), filename=payload.filename, raw_csv=payload.csv_text,
        checksum=checksum, source_type=payload.source_type,
        source_reference=payload.source_reference, mapping=payload.mapping, report=report,
        created_by=user.username, organization_id=organization_id)
    db.add(batch)
    try:
        revision(db, batch, user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This CSV already has a saved preview. Use import history to review and commit it.")
    return {"batch_id": batch.batch_id, "report": report, "source_type": batch.source_type}


@router.get("/batches")
def batches(db: Session = Depends(get_db), user: User = Depends(writer)):
    items = db.query(IntakeBatch).filter_by(organization_id=org(user)).order_by(IntakeBatch.created_at.desc()).limit(100).all()
    return [{"batch_id": b.batch_id, "filename": b.filename, "source_type": b.source_type, "source_reference": b.source_reference,
             "checksum": b.checksum, "created_by": b.created_by, "created_at": b.created_at, "status": b.status, "report": b.report} for b in items]


def entity(db, model, organization_id, **values):
    row = db.query(model).filter_by(organization_id=organization_id, **values).first()
    if row is None:
        row = model(organization_id=organization_id, **values)
        db.add(row)
        db.flush()
    return row


@router.post("/batches/{batch_id}/commit")
def commit(batch_id: str, db: Session = Depends(get_db), user: User = Depends(writer)):
    organization_id = org(user)
    # Serialize canonical commits within an organization on PostgreSQL,
    # including different batches carrying overlapping ET numbers.
    db.query(Organization).filter_by(organization_id=organization_id).with_for_update().one()
    batch = db.query(IntakeBatch).filter_by(batch_id=batch_id, organization_id=organization_id).with_for_update().first()
    if batch is None:
        raise HTTPException(404, "Import batch not found")
    if batch.status != "preview":
        raise HTTPException(409, "Batch has already been committed")
    if batch.source_type == "synthetic_demo":
        # The legacy analytics and model pipelines are intentionally untouched.
        # Keep demo rows in staging so those pipelines cannot treat them as observations.
        batch.status = "demo_staged"
        revision(db, batch, user)
        db.commit()
        return {"status": "demo_staged", "inserted": 0, "message": "Synthetic rows retained in staging, excluded from clinical records and scientific evaluation."}
    existing = {number for number, in db.query(ETTransfer.et_number).filter_by(organization_id=organization_id)}
    accepted, report = validate_csv(batch.raw_csv, batch.mapping, existing, embryo_identifiers(db, organization_id))
    if not accepted:
        raise HTTPException(409, "No eligible rows remain; records may already exist")
    try:
        for source_row, value in accepted:
            transfer = persist_case(db, value, organization_id, user.username, batch.source_type, batch.source_reference)
            db.add(TransferProvenance(organization_id=organization_id, transfer_id=transfer.transfer_id,
                batch_id=batch.batch_id, source_row=source_row, source_type=batch.source_type))
        batch.report = report
        batch.status = "committed"
        revision(db, batch, user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A conflicting record was created. No rows from this batch were committed.")
    return {"status": "committed", "inserted": len(accepted), "report": report}


@router.get("/schema")
def schema(user: User = Depends(writer)):
    org(user)
    return CanonicalET.model_json_schema()


class ManualInput(BaseModel):
    record: CanonicalET
    source_reference: str = Field(min_length=5, max_length=1000)


@router.post("/manual", status_code=201)
def manual(payload: ManualInput, db: Session = Depends(get_db), user: User = Depends(writer)):
    organization_id = org(user)
    db.query(Organization).filter_by(organization_id=organization_id).with_for_update().one()
    if db.query(ETTransfer).filter_by(organization_id=organization_id, et_number=payload.record.et_number).first():
        raise HTTPException(409, "ET number already exists in your organization")
    try:
        transfer = persist_case(db, payload.record, organization_id, user.username, "real_internal", payload.source_reference, action="manual_create")
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Conflicting reproductive identifier; no record was created")
    return {"transfer_id": transfer.transfer_id, "source_type": "real_internal"}


@router.get("/batches/{batch_id}/revisions")
def revisions(batch_id: str, db: Session = Depends(get_db), user: User = Depends(writer)):
    rows = db.query(IntakeRevision).filter_by(batch_id=batch_id, organization_id=org(user)).order_by(IntakeRevision.revision_id).all()
    return [{"revision_id": row.revision_id, "actor": row.actor, "created_at": row.created_at, **row.state} for row in rows]


@router.get("/batches/{batch_id}/source")
def source_csv(batch_id: str, db: Session = Depends(get_db), user: User = Depends(writer)):
    batch = db.query(IntakeBatch).filter_by(batch_id=batch_id, organization_id=org(user)).first()
    if batch is None:
        raise HTTPException(404, "Import batch not found")
    return Response(batch.raw_csv.encode("utf-8"), media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="ovulite-source-{batch.batch_id}.csv"'})
