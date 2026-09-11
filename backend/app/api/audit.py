"""Reading the audit trail.

Admin-only, and read-only: there is deliberately no endpoint that writes,
edits or deletes an audit row. A trail the application can rewrite through its
own API is not evidence of anything.

Scoped to the caller's organization, with one deliberate exception — an admin
can see failed logins that carry no organization, because an attempt against
an unknown username has none and dropping those would hide exactly the
attempts worth seeing.
"""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.database import get_db
from app.models.audit_event import AuditEvent
from app.models.user import User
from app.schemas.audit import AuditEventResponse, AuditPage

router = APIRouter()

ADMIN_ROLES = ("admin", "organization_admin")


@router.get("/events", response_model=AuditPage)
def list_events(
    event_type: str | None = Query(None),
    actor_user_id: int | None = Query(None),
    outcome: str | None = Query(None),
    target_type: str | None = Query(None),
    since_days: int = Query(30, ge=1, le=3650),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> AuditPage:
    """Recent audit events, newest first."""
    since = datetime.now().astimezone() - timedelta(days=since_days)
    query = db.query(AuditEvent).filter(AuditEvent.occurred_at >= since)

    # Org-scoped, plus the org-less rows (failed logins against unknown users).
    query = query.filter(
        or_(
            AuditEvent.organization_id == current_user.organization_id,
            AuditEvent.organization_id.is_(None),
        )
    )
    if event_type:
        query = query.filter(AuditEvent.event_type == event_type)
    if actor_user_id is not None:
        query = query.filter(AuditEvent.actor_user_id == actor_user_id)
    if outcome:
        query = query.filter(AuditEvent.outcome == outcome)
    if target_type:
        query = query.filter(AuditEvent.target_type == target_type)

    total = query.count()
    rows = (
        query.order_by(AuditEvent.occurred_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    earliest = (
        db.query(AuditEvent.occurred_at).order_by(AuditEvent.occurred_at.asc()).limit(1).scalar()
    )
    return AuditPage(
        items=[AuditEventResponse.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        earliest_event=earliest.date() if isinstance(earliest, datetime) else None,
        note=(
            "The trail starts when auditing was introduced; nothing before that was observed "
            "and none of it is reconstructed here. Details record which fields changed, not "
            "their values — clinical values are not copied into a log with a different audience."
        ),
    )


@router.get("/event-types", response_model=list[str])
def event_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*ADMIN_ROLES)),
) -> list[str]:
    """Event types actually present, so a filter offers only real options."""
    rows = db.query(AuditEvent.event_type).distinct().all()
    return sorted(r[0] for r in rows)
