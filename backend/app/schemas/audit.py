"""Schemas for reading the audit trail."""

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel


class AuditEventResponse(BaseModel):
    audit_id: int
    occurred_at: datetime
    event_type: str
    outcome: str
    actor_user_id: Optional[int]
    actor_label: Optional[str]
    """The username attempted. Present even when actor_user_id is null, which
    is the case for a login against an unknown account."""
    actor_role: Optional[str]
    organization_id: Optional[int]
    target_type: Optional[str]
    target_id: Optional[str]
    ip_address: Optional[str]
    request_id: Optional[str]
    detail: Optional[dict[str, Any]]
    message: Optional[str]

    model_config = {"from_attributes": True}


class AuditPage(BaseModel):
    items: list[AuditEventResponse]
    total: int
    page: int
    page_size: int
    earliest_event: Optional[date]
    """When the trail begins. Anything before this was not observed."""
    note: str
