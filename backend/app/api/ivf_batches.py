"""CRUD API endpoints for IVF Batches."""

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import LAB_WRITE_ROLES, get_current_user, require_role
from app.database import get_db
from app.models.ivf_batch import IVFBatch
from app.models.ivm_batch import IVMBatch
from app.models.opu_session import OPUSession
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.ivf_batch import IVFBatchCreate, IVFBatchResponse, IVFBatchUpdate

router = APIRouter()


def _build_detail(b: IVFBatch) -> dict:
    d = {c.name: getattr(b, c.name) for c in b.__table__.columns}
    d["opu_donor_tag"] = b.opu_session.donor.tag_id if b.opu_session and b.opu_session.donor else None
    d["opu_date"] = b.opu_session.opu_date if b.opu_session else None
    d["sire_name"] = b.sire.name if b.sire else None
    d["embryologist_name"] = b.embryologist.name if b.embryologist else None
    return d


def _with_joins(db: Session):
    return db.query(IVFBatch).options(
        joinedload(IVFBatch.opu_session).joinedload(OPUSession.donor),
        joinedload(IVFBatch.sire),
        joinedload(IVFBatch.embryologist),
    )


@router.get("/", response_model=PaginatedResponse[IVFBatchResponse])
def list_ivf_batches(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    opu_id: Optional[int] = None,
    sire_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List IVF batches with pagination, optionally filtered by OPU session or sire."""
    q = _with_joins(db).filter(IVFBatch.organization_id == current_user.organization_id)
    if opu_id is not None:
        q = q.filter(IVFBatch.opu_id == opu_id)
    if sire_id is not None:
        q = q.filter(IVFBatch.sire_id == sire_id)
    total = q.count()
    items = q.order_by(IVFBatch.ivf_batch_id).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse(
        items=[_build_detail(b) for b in items], total=total, page=page, page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/{ivf_batch_id}", response_model=IVFBatchResponse)
def get_ivf_batch(ivf_batch_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    b = _with_joins(db).filter(
        IVFBatch.ivf_batch_id == ivf_batch_id, IVFBatch.organization_id == current_user.organization_id
    ).first()
    if not b:
        raise HTTPException(status_code=404, detail="IVF batch not found")
    return _build_detail(b)


@router.post("/", response_model=IVFBatchResponse, status_code=status.HTTP_201_CREATED)
def create_ivf_batch(
    payload: IVFBatchCreate, db: Session = Depends(get_db), current_user: User = Depends(require_role(*LAB_WRITE_ROLES)),
):
    # The lab sequence is OPU -> IVM -> IVF. An IVF batch that does not come
    # from a recorded IVM batch of the same OPU session has skipped a stage.
    if payload.ivm_batch_id is None:
        raise HTTPException(422, "Record the IVM batch for this OPU session before creating the IVF batch.")
    ivm = db.query(IVMBatch).filter(
        IVMBatch.ivm_batch_id == payload.ivm_batch_id,
        IVMBatch.organization_id == current_user.organization_id,
    ).first()
    if ivm is None or ivm.opu_id != payload.opu_id:
        raise HTTPException(422, "The IVM batch does not belong to this OPU session.")
    b = IVFBatch(**payload.model_dump(), organization_id=current_user.organization_id)
    db.add(b)
    db.commit()
    db.refresh(b)
    return _build_detail(b)


@router.put("/{ivf_batch_id}", response_model=IVFBatchResponse)
def update_ivf_batch(
    ivf_batch_id: int, payload: IVFBatchUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_role(*LAB_WRITE_ROLES)),
):
    b = db.query(IVFBatch).filter(
        IVFBatch.ivf_batch_id == ivf_batch_id, IVFBatch.organization_id == current_user.organization_id
    ).first()
    if not b:
        raise HTTPException(status_code=404, detail="IVF batch not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(b, key, value)
    db.commit()
    db.refresh(b)
    return _build_detail(b)


@router.delete("/{ivf_batch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ivf_batch(ivf_batch_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role(*LAB_WRITE_ROLES))):
    b = db.query(IVFBatch).filter(
        IVFBatch.ivf_batch_id == ivf_batch_id, IVFBatch.organization_id == current_user.organization_id
    ).first()
    if not b:
        raise HTTPException(status_code=404, detail="IVF batch not found")
    db.delete(b)
    db.commit()
