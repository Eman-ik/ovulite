"""CRUD API endpoints for ET Transfers (the central entity)."""

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError
from fastapi.encoders import jsonable_encoder
from app.models.case_metadata import CaseMetadata, CaseAudit
from app.models.intake_batch import TransferProvenance
from app.models.organization import Organization

from app.auth.dependencies import ET_WRITE_ROLES, get_current_user, require_role
from app.database import get_db
from app.models.donor import Donor
from app.models.embryo import Embryo
from app.models.et_transfer import ETTransfer
from app.models.protocol import Protocol
from app.models.recipient import Recipient
from app.models.sire import Sire
from app.models.technician import Technician
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.et_transfer import (
    ETTransferCreate,
    ETTransferDetail,
    ETTransferNew,
    ETTransferResponse,
    ETTransferUpdate,
)

router = APIRouter()


def _validate_links(db, values, organization_id, transfer_id=None):
    if organization_id is None:
        raise HTTPException(403, "An organization is required")
    db.query(Organization).filter_by(organization_id=organization_id).with_for_update().one()
    for key, model, pk in (("recipient_id", Recipient, Recipient.recipient_id), ("embryo_id", Embryo, Embryo.embryo_id),
                          ("protocol_id", Protocol, Protocol.protocol_id), ("technician_id", Technician, Technician.technician_id)):
        if values.get(key) is not None and not db.query(model).filter(pk == values[key], model.organization_id == organization_id).first():
            raise HTTPException(422, f"{key} does not identify a record in your organization")
    if values.get("et_number") is not None:
        query = db.query(ETTransfer).filter_by(organization_id=organization_id, et_number=values["et_number"])
        if transfer_id is not None:
            query = query.filter(ETTransfer.transfer_id != transfer_id)
        if query.first():
            raise HTTPException(409, "ET number already exists in your organization")


def _audit_snapshot(db, transfer, user, action):
    metadata = db.query(CaseMetadata).filter_by(transfer_id=transfer.transfer_id, organization_id=user.organization_id).first()
    previous = dict(metadata.data) if metadata else None
    core = jsonable_encoder({column.name: getattr(transfer, column.name) for column in transfer.__table__.columns})
    if transfer.recipient:
        core.update(recipient_tag=transfer.recipient.tag_id, farm_location=transfer.farm_location)
    if transfer.embryo:
        embryo = transfer.embryo
        core.update(embryo_stage=embryo.stage, embryo_grade=embryo.grade, fresh_or_frozen=embryo.fresh_or_frozen,
            donor_tag=embryo.donor.tag_id if embryo.donor else None, sire_name=embryo.sire.name if embryo.sire else None)
    data = {**(previous or {}), **core}
    if metadata is None:
        metadata = CaseMetadata(transfer_id=transfer.transfer_id, organization_id=user.organization_id, data=data,
            source_type="real_internal" if action == "create" else "unclassified_legacy", source_reference="Manual record entry" if action == "create" else "Legacy record; original source not documented",
            version=1, updated_by=user.username)
        db.add(metadata)
    else:
        metadata.data = data
        metadata.version += 1
        metadata.updated_by = user.username
    db.add(CaseAudit(transfer_id=transfer.transfer_id, organization_id=user.organization_id, action=action, actor=user.username,
        details={"version": metadata.version, "before": previous, "after": data, "source_type": metadata.source_type}))


def _clean_pregnancy_result(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"pregnant", "p", "positive"}:
        return "Pregnant"
    if normalized in {"open", "o", "negative"}:
        return "Open"
    if normalized in {"recheck", "pending"}:
        return "Recheck"
    return None


def _build_detail(t: ETTransfer) -> dict:
    """Build ETTransferDetail dict with joined entity names."""
    d = {c.name: getattr(t, c.name) for c in t.__table__.columns}
    d["pc1_result"] = _clean_pregnancy_result(t.pc1_result)
    d["donor_tag"] = t.embryo.donor.tag_id if t.embryo and t.embryo.donor else None
    d["donor_breed"] = t.embryo.donor.breed if t.embryo and t.embryo.donor else None
    d["sire_name"] = t.embryo.sire.name if t.embryo and t.embryo.sire else None
    d["recipient_tag"] = t.recipient.tag_id if t.recipient else None
    d["technician_name"] = t.technician.name if t.technician else None
    d["protocol_name"] = t.protocol.name if t.protocol else None
    d["embryo_stage"] = t.embryo.stage if t.embryo else None
    d["embryo_grade"] = t.embryo.grade if t.embryo else None
    d["fresh_or_frozen"] = t.embryo.fresh_or_frozen if t.embryo else None
    return d


@router.get("/", response_model=PaginatedResponse[ETTransferDetail])
def list_transfers(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = None,
    protocol_id: Optional[int] = None,
    technician_id: Optional[int] = None,
    pc1_result: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List ET transfers with pagination, filters, and joined entity names."""
    q = db.query(ETTransfer).options(
        joinedload(ETTransfer.embryo).joinedload(Embryo.donor),
        joinedload(ETTransfer.embryo).joinedload(Embryo.sire),
        joinedload(ETTransfer.recipient),
        joinedload(ETTransfer.technician),
        joinedload(ETTransfer.protocol),
    ).filter(ETTransfer.organization_id == current_user.organization_id)
    if search:
        q = q.filter(
            ETTransfer.customer_id.ilike(f"%{search}%")
            | ETTransfer.farm_location.ilike(f"%{search}%")
        )
    if protocol_id is not None:
        q = q.filter(ETTransfer.protocol_id == protocol_id)
    if technician_id is not None:
        q = q.filter(ETTransfer.technician_id == technician_id)
    if pc1_result:
        q = q.filter(ETTransfer.pc1_result == pc1_result)

    total = q.count()
    items = q.order_by(ETTransfer.transfer_id).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse(
        items=[_build_detail(t) for t in items],
        total=total, page=page, page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/{transfer_id}", response_model=ETTransferDetail)
def get_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    t = (
        db.query(ETTransfer)
        .options(
            joinedload(ETTransfer.embryo).joinedload(Embryo.donor),
            joinedload(ETTransfer.embryo).joinedload(Embryo.sire),
            joinedload(ETTransfer.recipient),
            joinedload(ETTransfer.technician),
            joinedload(ETTransfer.protocol),
        )
        .filter(
            ETTransfer.transfer_id == transfer_id,
            ETTransfer.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not t:
        raise HTTPException(status_code=404, detail="Transfer not found")
    return _build_detail(t)


def _check_embryo_available(db, embryo_id, organization_id, exclude_transfer_id=None):
    """An embryo can be in one embryo-transfer record, and only if it is not
    already marked Transferred. Enforced here because nothing else stops a
    second ET for the same embryo."""
    if embryo_id is None:
        return
    embryo = db.query(Embryo).filter(
        Embryo.embryo_id == embryo_id, Embryo.organization_id == organization_id
    ).first()
    if embryo is not None and embryo.status == "Transferred":
        raise HTTPException(409, "This embryo is already marked Transferred and cannot be transferred again.")
    existing = db.query(ETTransfer).filter(
        ETTransfer.embryo_id == embryo_id, ETTransfer.organization_id == organization_id
    )
    if exclude_transfer_id is not None:
        existing = existing.filter(ETTransfer.transfer_id != exclude_transfer_id)
    if existing.first() is not None:
        raise HTTPException(409, "This embryo already has an embryo-transfer record.")


@router.post("/", response_model=ETTransferResponse, status_code=status.HTTP_201_CREATED)
def create_transfer(
    payload: ETTransferNew,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*ET_WRITE_ROLES)),
):
    """Create a new ET transfer record."""
    _validate_links(db, payload.model_dump(), current_user.organization_id)
    _check_embryo_available(db, payload.embryo_id, current_user.organization_id)
    transfer = ETTransfer(
        **payload.model_dump(), organization_id=current_user.organization_id
    )
    db.add(transfer)
    db.flush()
    _audit_snapshot(db, transfer, current_user, "create")
    db.commit()
    db.refresh(transfer)
    return transfer


@router.put("/{transfer_id}", response_model=ETTransferResponse)
def update_transfer(
    transfer_id: int,
    payload: ETTransferUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*ET_WRITE_ROLES)),
):
    t = (
        db.query(ETTransfer)
        .filter(
            ETTransfer.transfer_id == transfer_id,
            ETTransfer.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not t:
        raise HTTPException(status_code=404, detail="Transfer not found")
    combined = {key: getattr(t, key) for key in ETTransferCreate.model_fields}
    combined.update(payload.model_dump(exclude_unset=True))
    try:
        ETTransferCreate.model_validate(combined)
    except ValidationError as error:
        raise HTTPException(422, detail=jsonable_encoder(error.errors(), custom_encoder={ValueError: str}))
    _validate_links(db, combined, current_user.organization_id, transfer_id)
    if "embryo_id" in payload.model_dump(exclude_unset=True):
        _check_embryo_available(db, combined.get("embryo_id"), current_user.organization_id, transfer_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(t, key, value)
    db.flush()
    db.expire(t, ["recipient", "embryo", "protocol", "technician"])
    _audit_snapshot(db, t, current_user, "update")
    db.commit()
    db.refresh(t)
    return t


@router.delete("/{transfer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*ET_WRITE_ROLES)),
):
    t = (
        db.query(ETTransfer)
        .filter(
            ETTransfer.transfer_id == transfer_id,
            ETTransfer.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not t:
        raise HTTPException(status_code=404, detail="Transfer not found")
    metadata = db.query(CaseMetadata).filter_by(transfer_id=transfer_id, organization_id=current_user.organization_id).first()
    db.add(CaseAudit(transfer_id=transfer_id, organization_id=current_user.organization_id, action="delete", actor=current_user.username,
        details={"record": metadata.data if metadata else jsonable_encoder({c.name: getattr(t, c.name) for c in t.__table__.columns})}))
    db.query(TransferProvenance).filter_by(transfer_id=transfer_id, organization_id=current_user.organization_id).delete()
    if metadata:
        db.delete(metadata)
    db.flush()
    db.delete(t)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This transfer has dependent records and cannot be deleted")
