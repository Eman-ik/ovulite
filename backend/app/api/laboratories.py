"""CRUD for Laboratory — the site entity that replaced free-text ``farm_location``.

Reads are open to any authenticated role: a site picker appears on nearly every
data-entry form, and a viewer needs to see which site a transfer belongs to.
Writes are admin-only, because renaming or deactivating a site re-labels every
transfer, OPU session and recipient attached to it.
"""

import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_role
from app.database import get_db
from app.models.et_transfer import ETTransfer
from app.models.laboratory import Laboratory
from app.models.opu_session import OPUSession
from app.models.recipient import Recipient
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.laboratory import (
    LaboratoryCreate,
    LaboratoryResponse,
    LaboratoryUpdate,
    LaboratoryUsage,
)

router = APIRouter()

ADMIN_ROLES = ("admin", "organization_admin")


def _owned(laboratory_id: int, db: Session, user: User) -> Laboratory:
    lab = (
        db.query(Laboratory)
        .filter(
            Laboratory.laboratory_id == laboratory_id,
            Laboratory.organization_id == user.organization_id,
        )
        .first()
    )
    if lab is None:
        raise HTTPException(status_code=404, detail="Laboratory not found")
    return lab


def _usage(lab: Laboratory, db: Session) -> LaboratoryUsage:
    return LaboratoryUsage(
        laboratory_id=lab.laboratory_id,
        name=lab.name,
        transfers=db.query(ETTransfer).filter(ETTransfer.laboratory_id == lab.laboratory_id).count(),
        opu_sessions=db.query(OPUSession).filter(OPUSession.laboratory_id == lab.laboratory_id).count(),
        recipients=db.query(Recipient).filter(Recipient.laboratory_id == lab.laboratory_id).count(),
    )


@router.get("/", response_model=PaginatedResponse[LaboratoryResponse])
def list_laboratories(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    include_inactive: bool = Query(False, description="Include deactivated sites"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Laboratory).filter(Laboratory.organization_id == current_user.organization_id)
    if not include_inactive:
        q = q.filter(Laboratory.active.is_(True))
    total = q.count()
    items = (
        q.order_by(Laboratory.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedResponse(
        items=items, total=total, page=page, page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/{laboratory_id}", response_model=LaboratoryResponse)
def get_laboratory(
    laboratory_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _owned(laboratory_id, db, current_user)


@router.get("/{laboratory_id}/usage", response_model=LaboratoryUsage)
def get_laboratory_usage(
    laboratory_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """What is attached to this site — shown before deactivating it."""
    return _usage(_owned(laboratory_id, db, current_user), db)


@router.post("/", response_model=LaboratoryResponse, status_code=status.HTTP_201_CREATED)
def create_laboratory(
    payload: LaboratoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
):
    existing = (
        db.query(Laboratory)
        .filter(
            Laboratory.organization_id == current_user.organization_id,
            Laboratory.name == payload.name,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"A site named '{payload.name}' already exists in this organization.",
        )
    lab = Laboratory(**payload.model_dump(), organization_id=current_user.organization_id)
    db.add(lab)
    db.commit()
    db.refresh(lab)
    return lab


@router.put("/{laboratory_id}", response_model=LaboratoryResponse)
def update_laboratory(
    laboratory_id: int,
    payload: LaboratoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
):
    lab = _owned(laboratory_id, db, current_user)
    changes = payload.model_dump(exclude_unset=True)

    new_name = changes.get("name")
    if new_name and new_name != lab.name:
        clash = (
            db.query(Laboratory)
            .filter(
                Laboratory.organization_id == current_user.organization_id,
                Laboratory.name == new_name,
                Laboratory.laboratory_id != laboratory_id,
            )
            .first()
        )
        if clash is not None:
            raise HTTPException(
                status_code=409, detail=f"A site named '{new_name}' already exists."
            )

    for field, value in changes.items():
        setattr(lab, field, value)
    db.commit()
    db.refresh(lab)
    return lab


@router.delete("/{laboratory_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_laboratory(
    laboratory_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
):
    """Deactivate, or delete outright only if nothing references the site.

    A site with transfers behind it cannot be deleted: the foreign keys would
    orphan and every historical record would lose its location. Deactivating
    removes it from pickers while leaving the history readable.
    """
    lab = _owned(laboratory_id, db, current_user)
    usage = _usage(lab, db)
    attached = usage.transfers + usage.opu_sessions + usage.recipients
    if attached == 0:
        db.delete(lab)
    else:
        lab.active = False
    db.commit()
    return None
