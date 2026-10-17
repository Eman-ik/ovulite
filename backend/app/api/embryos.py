"""CRUD API endpoints for Embryos."""

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import LAB_WRITE_ROLES, get_current_user, require_role
from app.database import get_db
from app.models.embryo import Embryo
from app.models.ivf_batch import IVFBatch
from app.models.opu_session import OPUSession
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.embryo import EmbryoCreate, EmbryoResponse, EmbryoUpdate

router = APIRouter()


def _resolve_lab_links(
    db: Session, org_id: int, opu_id: Optional[int], ivf_batch_id: Optional[int]
) -> tuple[Optional[int], Optional[int]]:
    """Check an embryo's OPU session and IVF batch belong to this organization and to
    each other, and return the (opu_id, ivf_batch_id) to store. An IVF batch implies
    its OPU session, so a batch given without one takes the batch's session."""
    if ivf_batch_id is not None:
        batch = db.query(IVFBatch).filter(
            IVFBatch.ivf_batch_id == ivf_batch_id, IVFBatch.organization_id == org_id
        ).first()
        if batch is None:
            raise HTTPException(status_code=422, detail="IVF batch not found")
        if opu_id is not None and batch.opu_id != opu_id:
            raise HTTPException(status_code=422, detail="The IVF batch does not come from this OPU session.")
        return batch.opu_id, ivf_batch_id
    if opu_id is not None and db.query(OPUSession.opu_id).filter(
        OPUSession.opu_id == opu_id, OPUSession.organization_id == org_id
    ).first() is None:
        raise HTTPException(status_code=422, detail="OPU session not found")
    return opu_id, None


@router.get("/", response_model=PaginatedResponse[EmbryoResponse])
def list_embryos(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    donor_id: Optional[int] = None,
    sire_id: Optional[int] = None,
    fresh_or_frozen: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Embryo).filter(Embryo.organization_id == current_user.organization_id)
    if donor_id is not None:
        q = q.filter(Embryo.donor_id == donor_id)
    if sire_id is not None:
        q = q.filter(Embryo.sire_id == sire_id)
    if fresh_or_frozen:
        q = q.filter(Embryo.fresh_or_frozen == fresh_or_frozen)
    total = q.count()
    items = q.order_by(Embryo.embryo_id).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse(
        items=items, total=total, page=page, page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/{embryo_id}", response_model=EmbryoResponse)
def get_embryo(embryo_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    e = db.query(Embryo).filter(
        Embryo.embryo_id == embryo_id, Embryo.organization_id == current_user.organization_id
    ).first()
    if not e:
        raise HTTPException(status_code=404, detail="Embryo not found")
    return e


@router.post("/", response_model=EmbryoResponse, status_code=status.HTTP_201_CREATED)
def create_embryo(
    payload: EmbryoCreate, db: Session = Depends(get_db), current_user: User = Depends(require_role(*LAB_WRITE_ROLES)),
):
    values = payload.model_dump()
    values["opu_id"], values["ivf_batch_id"] = _resolve_lab_links(
        db, current_user.organization_id, values["opu_id"], values["ivf_batch_id"]
    )
    e = Embryo(**values, organization_id=current_user.organization_id)
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


@router.put("/{embryo_id}", response_model=EmbryoResponse)
def update_embryo(
    embryo_id: int, payload: EmbryoUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_role(*LAB_WRITE_ROLES)),
):
    e = db.query(Embryo).filter(
        Embryo.embryo_id == embryo_id, Embryo.organization_id == current_user.organization_id
    ).first()
    if not e:
        raise HTTPException(status_code=404, detail="Embryo not found")
    values = payload.model_dump(exclude_unset=True)
    if "opu_id" in values or "ivf_batch_id" in values:
        # Check the link as it will stand after this update, not just the fields sent.
        values["opu_id"], values["ivf_batch_id"] = _resolve_lab_links(
            db, current_user.organization_id,
            values.get("opu_id", e.opu_id), values.get("ivf_batch_id", e.ivf_batch_id),
        )
    for key, value in values.items():
        setattr(e, key, value)
    db.commit()
    db.refresh(e)
    return e


@router.delete("/{embryo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_embryo(embryo_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role(*LAB_WRITE_ROLES))):
    e = db.query(Embryo).filter(
        Embryo.embryo_id == embryo_id, Embryo.organization_id == current_user.organization_id
    ).first()
    if not e:
        raise HTTPException(status_code=404, detail="Embryo not found")
    db.delete(e)
    db.commit()
