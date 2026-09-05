"""CRUD API endpoints for OPU Sessions."""

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.opu_session import OPUSession
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.opu_session import OPUSessionCreate, OPUSessionResponse, OPUSessionUpdate

router = APIRouter()


def _build_detail(s: OPUSession) -> dict:
    d = {c.name: getattr(s, c.name) for c in s.__table__.columns}
    d["donor_tag"] = s.donor.tag_id if s.donor else None
    d["technician_name"] = s.technician.name if s.technician else None
    return d


def _with_joins(db: Session):
    return db.query(OPUSession).options(
        joinedload(OPUSession.donor), joinedload(OPUSession.technician)
    )


@router.get("/", response_model=PaginatedResponse[OPUSessionResponse])
def list_opu_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    donor_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List OPU sessions with pagination, optionally filtered by donor."""
    q = _with_joins(db).filter(OPUSession.organization_id == current_user.organization_id)
    if donor_id is not None:
        q = q.filter(OPUSession.donor_id == donor_id)
    total = q.count()
    items = q.order_by(OPUSession.opu_id).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse(
        items=[_build_detail(s) for s in items], total=total, page=page, page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/{opu_id}", response_model=OPUSessionResponse)
def get_opu_session(opu_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    s = _with_joins(db).filter(
        OPUSession.opu_id == opu_id, OPUSession.organization_id == current_user.organization_id
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="OPU session not found")
    return _build_detail(s)


@router.post("/", response_model=OPUSessionResponse, status_code=status.HTTP_201_CREATED)
def create_opu_session(
    payload: OPUSessionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    s = OPUSession(**payload.model_dump(), organization_id=current_user.organization_id)
    db.add(s)
    db.commit()
    db.refresh(s)
    return _build_detail(s)


@router.put("/{opu_id}", response_model=OPUSessionResponse)
def update_opu_session(
    opu_id: int, payload: OPUSessionUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user),
):
    s = db.query(OPUSession).filter(
        OPUSession.opu_id == opu_id, OPUSession.organization_id == current_user.organization_id
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="OPU session not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(s, key, value)
    db.commit()
    db.refresh(s)
    return _build_detail(s)


@router.delete("/{opu_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_opu_session(opu_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    s = db.query(OPUSession).filter(
        OPUSession.opu_id == opu_id, OPUSession.organization_id == current_user.organization_id
    ).first()
    if not s:
        raise HTTPException(status_code=404, detail="OPU session not found")
    db.delete(s)
    db.commit()
