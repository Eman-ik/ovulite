"""Recording audit events.

The contract this module keeps: **auditing must never break the thing it is
auditing.** A write that fails to log is a gap in the trail; a write that
fails *because* logging failed is an outage. So ``record()`` swallows its own
errors and reports them to the application log instead, and it never commits —
it joins whatever transaction the caller is already in, so an audit row for a
rolled-back change disappears with the change.

The one exception is authentication. A failed login has no surrounding
transaction to join and must survive regardless, so ``record_auth()`` commits
on its own session.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit_event import (
    OUTCOME_SUCCESS,
    AuditEvent,
)
from app.models.user import User

logger = logging.getLogger(__name__)

# Never write these to the trail, whatever a caller passes.
_REDACTED_KEYS = {
    "password",
    "password_hash",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "authorization",
    "api_key",
}


def _safe_detail(detail: dict[str, Any] | None) -> dict[str, Any] | None:
    """Strip anything sensitive, and keep field *names* rather than values.

    Callers pass what changed; this keeps the shape of the change without
    copying clinical values into a log that a different audience reads.
    """
    if not detail:
        return None
    cleaned: dict[str, Any] = {}
    for key, value in detail.items():
        if key.lower() in _REDACTED_KEYS:
            cleaned[key] = "[redacted]"
        elif isinstance(value, (list, tuple, set)):
            cleaned[key] = sorted(str(v) for v in value)[:50]
        elif isinstance(value, dict):
            cleaned[key] = sorted(value.keys())[:50]
        elif isinstance(value, (str, int, float, bool)) or value is None:
            cleaned[key] = value
        else:
            cleaned[key] = str(value)[:200]
    return cleaned


def _request_context(request: Request | None) -> dict[str, Any]:
    if request is None:
        return {}
    client_host = request.client.host if request.client else None
    return {
        "ip_address": request.headers.get("x-forwarded-for", client_host),
        "user_agent": (request.headers.get("user-agent") or "")[:300] or None,
        "request_id": getattr(request.state, "request_id", None),
    }


def record(
    db: Session,
    event_type: str,
    *,
    actor: User | None = None,
    actor_label: str | None = None,
    organization_id: int | None = None,
    target_type: str | None = None,
    target_id: Any = None,
    outcome: str = OUTCOME_SUCCESS,
    detail: dict[str, Any] | None = None,
    message: str | None = None,
    request: Request | None = None,
) -> None:
    """Add an audit row to the caller's transaction.

    Does not commit: the row lands if and only if the change it describes
    does. Failures here are logged and swallowed — see the module docstring.
    """
    try:
        event = AuditEvent(
            event_type=event_type,
            outcome=outcome,
            actor_user_id=actor.user_id if actor else None,
            actor_label=actor_label or (actor.username if actor else None),
            actor_role=actor.role if actor else None,
            organization_id=organization_id
            if organization_id is not None
            else (actor.organization_id if actor else None),
            target_type=target_type,
            target_id=None if target_id is None else str(target_id),
            detail=_safe_detail(detail),
            message=message,
            **_request_context(request),
        )
        db.add(event)
    except Exception:  # pragma: no cover - defensive
        logger.exception("Failed to record audit event %s", event_type)


def record_auth(
    session_factory,
    event_type: str,
    *,
    actor: User | None = None,
    actor_label: str | None = None,
    outcome: str = OUTCOME_SUCCESS,
    message: str | None = None,
    request: Request | None = None,
) -> None:
    """Record an authentication event on its own committed session.

    A failed login is the event most worth keeping and has no successful
    transaction to ride along with, so this one commits independently.
    """
    db = session_factory()
    try:
        record(
            db,
            event_type,
            actor=actor,
            actor_label=actor_label,
            outcome=outcome,
            message=message,
            request=request,
            target_type="user",
            target_id=actor.user_id if actor else None,
        )
        db.commit()
    except Exception:  # pragma: no cover - defensive
        logger.exception("Failed to commit auth audit event %s", event_type)
        db.rollback()
    finally:
        db.close()


# ── Automatic auditing of clinical writes ────────────────
#
# Recording each write by hand in every router means the next router someone
# adds is silently unaudited. A session-level listener observes what is about
# to be flushed and writes the audit rows itself, so coverage is a property of
# the model being audited rather than of a developer remembering.
#
# Two details this went through the wrong way first, worth stating so they are
# not undone:
#
# 1. The actor is carried on ``Session.info``, not a ContextVar. FastAPI runs
#    sync dependencies in a worker thread, so a ContextVar set inside
#    ``get_current_user`` lands in a context copy that is discarded when the
#    dependency returns — the endpoint then flushes with an empty actor. The
#    Session is the one object that genuinely spans dependency and handler.
#
# 2. Rows are written in ``after_flush``, not ``before_flush``. An
#    autoincrement primary key does not exist until the INSERT has run, so
#    auditing an insert any earlier records ``target_id: None``. They are
#    written with a direct INSERT rather than ``session.add`` because adding
#    ORM objects during a flush re-enters the unit of work.

from sqlalchemy import event, inspect as sa_inspect
from sqlalchemy.orm import Session as SASession

from app.models.audit_event import RECORD_CREATED, RECORD_DELETED, RECORD_UPDATED

_ACTOR_KEY = "ovulite_audit_actor"
_PENDING_KEY = "ovulite_audit_pending"

# Tables whose changes are privileged enough to audit. audit_events itself is
# excluded — auditing the audit would recurse.
AUDITED_TABLES = {
    "donors": "donor",
    "sires": "sire",
    "embryos": "embryo",
    "recipients": "recipient",
    "et_transfers": "et_transfer",
    "opu_sessions": "opu_session",
    "ivf_batches": "ivf_batch",
    "ivm_batches": "ivm_batch",
    "protocols": "protocol",
    "protocol_steps": "protocol_step",
    "technicians": "technician",
    "users": "user",
    "pregnancy_checks": "pregnancy_check",
    "calving_records": "calving_record",
    "recipient_evaluations": "recipient_evaluation",
    "synchronization_enrollments": "synchronization_enrollment",
    "embryo_observations": "embryo_observation",
    # A retrain decision, and the admin acknowledging it, is a privileged
    # change worth attributing. model_metrics is deliberately absent: it is a
    # machine-written snapshot, one row per day updated in place, so auditing
    # it would bury the human actions above in noise.
    "retrain_jobs": "retrain_job",
}


def set_audit_actor(
    db: Session,
    user_id: int | None,
    username: str | None,
    role: str | None,
    organization_id: int | None,
    request: Request | None = None,
) -> None:
    """Bind the acting user to this session, for the flush listener to read."""
    db.info[_ACTOR_KEY] = {
        "actor_user_id": user_id,
        "actor_label": username,
        "actor_role": role,
        "organization_id": organization_id,
        **_request_context(request),
    }


def _primary_key(instance) -> str | None:
    try:
        state = sa_inspect(instance)
        if state.identity:
            return ",".join(str(v) for v in state.identity)
        pk_values = [getattr(instance, c.name, None) for c in state.mapper.primary_key]
        return ",".join(str(v) for v in pk_values if v is not None) or None
    except Exception:  # pragma: no cover - defensive
        return None


def _changed_fields(instance) -> list[str]:
    """Names of columns whose value actually changed — never their values."""
    try:
        state = sa_inspect(instance)
        return sorted(
            attr.key
            for attr in state.mapper.column_attrs
            if state.attrs[attr.key].history.has_changes()
        )
    except Exception:  # pragma: no cover - defensive
        return []


@event.listens_for(SASession, "before_flush")
def _collect_audit_targets(session, _flush_context, _instances):  # pragma: no cover
    """Note what is changing, while the change history is still readable."""
    pending = session.info.setdefault(_PENDING_KEY, [])
    for collection, event_type in (
        (session.new, RECORD_CREATED),
        (session.dirty, RECORD_UPDATED),
        (session.deleted, RECORD_DELETED),
    ):
        for instance in list(collection):
            target_type = AUDITED_TABLES.get(getattr(instance, "__tablename__", None))
            if target_type is None:
                continue
            changed: list[str] = []
            if event_type == RECORD_UPDATED:
                if not session.is_modified(instance):
                    continue
                changed = _changed_fields(instance)
                if not changed:
                    continue
                if changed == ["last_login"]:
                    # Login bookkeeping, written before anyone is authenticated
                    # — so it has no actor, and auth.login.success already
                    # records the same event with one.
                    continue
            # Deletes lose their identity after the flush, so capture it now.
            pending.append((instance, event_type, target_type, changed, _primary_key(instance)))


@event.listens_for(SASession, "after_flush")
def _write_audit_rows(session, _flush_context):  # pragma: no cover - exercised via API
    """Write the rows, now that inserted primary keys exist."""
    pending = session.info.pop(_PENDING_KEY, None)
    if not pending:
        return
    context = session.info.get(_ACTOR_KEY) or {}

    rows = []
    for instance, event_type, target_type, changed, pre_flush_pk in pending:
        target_id = _primary_key(instance) or pre_flush_pk
        rows.append(
            {
                "event_type": event_type,
                "outcome": OUTCOME_SUCCESS,
                "actor_user_id": context.get("actor_user_id"),
                "actor_label": context.get("actor_label"),
                "actor_role": context.get("actor_role"),
                "organization_id": context.get("organization_id")
                or getattr(instance, "organization_id", None),
                "target_type": target_type,
                "target_id": target_id,
                "ip_address": context.get("ip_address"),
                "user_agent": context.get("user_agent"),
                "request_id": context.get("request_id"),
                "detail": _safe_detail({"changed_fields": changed}) if changed else None,
                "message": None,
            }
        )

    try:
        # A direct INSERT rather than session.add(): adding ORM objects during
        # a flush re-enters the unit of work. This runs in the same
        # transaction, so the audit row still lives or dies with the change.
        session.execute(AuditEvent.__table__.insert(), rows)
    except Exception:  # pragma: no cover - defensive
        logger.exception("Failed to write %d audit row(s)", len(rows))
