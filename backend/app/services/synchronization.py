"""Derive synchronization schedules and the vet's daily board.

The schedule is computed, never stored: each ``ProtocolStep`` becomes
``enrollment.start_date + step.day_offset``. Storing it would mean rewriting
every enrollment's rows whenever a protocol was corrected, and the copies
would drift the first time that was missed.

Step state is derived by comparing the due date to today and to whatever
``ProtocolLog`` rows exist for that enrollment:

    Done      a log exists for the step
    Overdue   due before today, no log
    Due today due today, no log
    Upcoming  due after today

"Overdue" deliberately does not become "Missed" on its own. A treatment given
but not yet typed in looks identical to one that never happened, and only the
person who was there knows which — so the board flags it for attention rather
than recording a clinical failure that may not have occurred.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Iterable

from app.models.protocol_log import ProtocolLog
from app.models.protocol_step import ProtocolStep
from app.models.synchronization_enrollment import SynchronizationEnrollment

DONE = "Done"
OVERDUE = "Overdue"
DUE_TODAY = "Due today"
UPCOMING = "Upcoming"


@dataclass
class ScheduledStep:
    step_id: int
    day_offset: int
    step_name: str
    drug_name: str | None
    dosage: str | None
    route: str | None
    is_transfer_day: bool
    due_date: date
    state: str
    completed_on: date | None
    days_from_today: int


@dataclass
class EnrollmentSchedule:
    enrollment_id: int
    recipient_id: int
    recipient_tag: str | None
    protocol_id: int
    protocol_name: str | None
    start_date: date
    status: str
    transfer_id: int | None
    steps: list[ScheduledStep] = field(default_factory=list)

    # Summary fields the board sorts and filters on.
    has_schedule: bool = True
    """False when the protocol has no steps defined yet — the enrollment is
    real but Ovulite cannot say what is due, and says so rather than
    presenting an empty schedule as 'nothing to do'."""
    next_step: ScheduledStep | None = None
    overdue_count: int = 0
    completed_count: int = 0
    total_steps: int = 0
    transfer_due_date: date | None = None
    current_stage: str = ""


def _log_index(logs: Iterable[ProtocolLog]) -> dict[int, date | None]:
    """step_id -> the date it was logged, for steps that have a log."""
    index: dict[int, date | None] = {}
    for log in logs:
        if log.step_id is None:
            continue
        existing = index.get(log.step_id)
        if existing is None or (log.step_date and log.step_date < existing):
            index[log.step_id] = log.step_date
    return index


def build_schedule(
    enrollment: SynchronizationEnrollment,
    steps: list[ProtocolStep],
    today: date | None = None,
) -> EnrollmentSchedule:
    """Expand one enrollment against its protocol's step template."""
    today = today or date.today()
    logged = _log_index(enrollment.logs)

    schedule = EnrollmentSchedule(
        enrollment_id=enrollment.enrollment_id,
        recipient_id=enrollment.recipient_id,
        recipient_tag=enrollment.recipient.tag_id if enrollment.recipient else None,
        protocol_id=enrollment.protocol_id,
        protocol_name=enrollment.protocol.name if enrollment.protocol else None,
        start_date=enrollment.start_date,
        status=enrollment.status,
        transfer_id=enrollment.transfer_id,
        has_schedule=bool(steps),
        total_steps=len(steps),
    )

    if not steps:
        schedule.current_stage = "No schedule defined for this protocol"
        return schedule

    for step in sorted(steps, key=lambda s: (s.day_offset, s.step_name)):
        due = enrollment.start_date + timedelta(days=step.day_offset)
        done_on = logged.get(step.step_id)
        if step.step_id in logged:
            state = DONE
        elif due < today:
            state = OVERDUE
        elif due == today:
            state = DUE_TODAY
        else:
            state = UPCOMING

        scheduled = ScheduledStep(
            step_id=step.step_id,
            day_offset=step.day_offset,
            step_name=step.step_name,
            drug_name=step.drug_name,
            dosage=step.dosage,
            route=step.route,
            is_transfer_day=step.is_transfer_day,
            due_date=due,
            state=state,
            completed_on=done_on,
            days_from_today=(due - today).days,
        )
        schedule.steps.append(scheduled)
        if step.is_transfer_day:
            schedule.transfer_due_date = due

    schedule.overdue_count = sum(1 for s in schedule.steps if s.state == OVERDUE)
    schedule.completed_count = sum(1 for s in schedule.steps if s.state == DONE)

    pending = [s for s in schedule.steps if s.state != DONE]
    schedule.next_step = pending[0] if pending else None

    if enrollment.status != "Active":
        schedule.current_stage = enrollment.status
    elif schedule.next_step is None:
        schedule.current_stage = "All steps recorded"
    elif schedule.overdue_count:
        schedule.current_stage = f"{schedule.overdue_count} step(s) overdue"
    else:
        nxt = schedule.next_step
        when = (
            "today"
            if nxt.days_from_today == 0
            else f"in {nxt.days_from_today} day(s)"
            if nxt.days_from_today > 0
            else f"{abs(nxt.days_from_today)} day(s) ago"
        )
        schedule.current_stage = f"{nxt.step_name} {when}"

    return schedule
