"""CRUD API endpoints for Protocol Logs (synchronization protocol steps)."""

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import ET_WRITE_ROLES, get_current_user, require_role
from app.database import get_db
from app.models.protocol_log import ProtocolLog
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.protocol_log import ProtocolLogCreate, ProtocolLogResponse, ProtocolLogUpdate

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[ProtocolLogResponse])
def list_protocol_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    transfer_id: Optional[int] = None,
    protocol_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List protocol log entries, optionally filtered by transfer or protocol."""
    q = db.query(ProtocolLog).filter(ProtocolLog.organization_id == current_user.organization_id)
    if transfer_id is not None:
        q = q.filter(ProtocolLog.transfer_id == transfer_id)
    if protocol_id is not None:
        q = q.filter(ProtocolLog.protocol_id == protocol_id)
    total = q.count()
    items = q.order_by(ProtocolLog.log_id).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse(
        items=items, total=total, page=page, page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/{log_id}", response_model=ProtocolLogResponse)
def get_protocol_log(log_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    log = db.query(ProtocolLog).filter(
        ProtocolLog.log_id == log_id, ProtocolLog.organization_id == current_user.organization_id
    ).first()
    if not log:
        raise HTTPException(status_code=404, detail="Protocol log entry not found")
    return log


@router.post("/", response_model=ProtocolLogResponse, status_code=status.HTTP_201_CREATED)
def create_protocol_log(
    payload: ProtocolLogCreate, db: Session = Depends(get_db), current_user: User = Depends(require_role(*ET_WRITE_ROLES)),
):
    log = ProtocolLog(**payload.model_dump(), organization_id=current_user.organization_id)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.put("/{log_id}", response_model=ProtocolLogResponse)
def update_protocol_log(
    log_id: int, payload: ProtocolLogUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_role(*ET_WRITE_ROLES)),
):
    log = db.query(ProtocolLog).filter(
        ProtocolLog.log_id == log_id, ProtocolLog.organization_id == current_user.organization_id
    ).first()
    if not log:
        raise HTTPException(status_code=404, detail="Protocol log entry not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(log, key, value)
    db.commit()
    db.refresh(log)
    return log


@router.delete("/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_protocol_log(log_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_role(*ET_WRITE_ROLES))):
    log = db.query(ProtocolLog).filter(
        ProtocolLog.log_id == log_id, ProtocolLog.organization_id == current_user.organization_id
    ).first()
    if not log:
        raise HTTPException(status_code=404, detail="Protocol log entry not found")
    db.delete(log)
    db.commit()
