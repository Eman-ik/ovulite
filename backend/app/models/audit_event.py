"""System-wide audit trail for auth events and privileged changes.

FR-M1-05 and NFR-SEC-06 require that who did what, and when, is answerable
after the fact. ``case_audit`` already covers edits to a single case, but it
cannot answer "who logged in", "who changed someone's role", or "who deployed
a model" — which are the questions an audit is actually for.

Design choices worth stating:

* **Append-only in practice.** Nothing in the application updates or deletes a
  row here. An audit trail that the application can rewrite is not evidence.
* **``actor_user_id`` is nullable.** A failed login has no authenticated
  actor, and that is exactly the event most worth recording. The attempted
  username is kept in ``actor_label`` so the row is still meaningful.
* **``organization_id`` is nullable**, unlike every other table: a failed
  login against an unknown username belongs to no organization, and forcing
  one would mean either inventing it or dropping the row.
* **No request bodies.** ``detail`` holds a small JSON summary — which fields
  changed, not their contents. Clinical values do not belong in a log that is
  read by people who may not be entitled to see them, and passwords must never
  reach it at all.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User

# Event families. Kept as plain strings rather than an enum so that adding an
# event type never requires a migration — an audit log that is awkward to
# extend is an audit log people route around.
AUTH_LOGIN_SUCCESS = "auth.login.success"
AUTH_LOGIN_FAILURE = "auth.login.failure"
AUTH_LOGOUT = "auth.logout"
AUTH_TOKEN_REFRESH = "auth.token.refresh"
USER_CREATED = "user.created"
USER_ROLE_CHANGED = "user.role_changed"
RECORD_CREATED = "record.created"
RECORD_UPDATED = "record.updated"
RECORD_DELETED = "record.deleted"
MODEL_DEPLOYED = "model.deployed"
PIPELINE_RUN = "pipeline.run"

OUTCOME_SUCCESS = "success"
OUTCOME_FAILURE = "failure"
OUTCOME_DENIED = "denied"

# JSONB on Postgres, JSON elsewhere, so the test suite's SQLite engine works.
_JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    audit_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    occurred_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)

    event_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False, default=OUTCOME_SUCCESS)

    # Null for unauthenticated events; actor_label still identifies the attempt.
    actor_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.user_id"), index=True)
    actor_label: Mapped[Optional[str]] = mapped_column(String(150))
    actor_role: Mapped[Optional[str]] = mapped_column(String(40))
    organization_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("organizations.organization_id"), index=True
    )

    # What was acted on, e.g. ("et_transfer", 489).
    target_type: Mapped[Optional[str]] = mapped_column(String(60), index=True)
    target_id: Mapped[Optional[str]] = mapped_column(String(60))

    ip_address: Mapped[Optional[str]] = mapped_column(String(64))
    user_agent: Mapped[Optional[str]] = mapped_column(String(300))
    request_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)

    # Field names and counts only — never values. See the module docstring.
    detail: Mapped[Optional[dict]] = mapped_column(_JSON_TYPE)
    message: Mapped[Optional[str]] = mapped_column(Text)

    actor: Mapped[Optional["User"]] = relationship()

    __table_args__ = (
        # The two queries an audit actually gets: "what happened recently" and
        # "everything this actor did".
        Index("ix_audit_events_org_time", "organization_id", "occurred_at"),
        Index("ix_audit_events_actor_time", "actor_user_id", "occurred_at"),
    )
