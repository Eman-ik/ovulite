"""Tests for synchronization schedule derivation.

The schedule is computed rather than stored, so these pin the arithmetic and
the state machine. ``today`` is always passed explicitly — a test that relies
on the real clock passes in the morning and fails after midnight.
"""

from datetime import date, timedelta

import pytest

from app.services.synchronization import (
    DONE,
    DUE_TODAY,
    OVERDUE,
    UPCOMING,
    build_schedule,
)

TODAY = date(2026, 9, 11)


class FakeStep:
    def __init__(self, step_id, day_offset, step_name, is_transfer_day=False):
        self.step_id = step_id
        self.day_offset = day_offset
        self.step_name = step_name
        self.drug_name = None
        self.dosage = None
        self.route = None
        self.is_transfer_day = is_transfer_day


class FakeLog:
    def __init__(self, step_id, step_date):
        self.step_id = step_id
        self.step_date = step_date


class FakeEnrollment:
    def __init__(self, start_date, logs=None, status="Active", transfer_id=None):
        self.enrollment_id = 1
        self.recipient_id = 7
        self.recipient = type("R", (), {"tag_id": "R-7"})()
        self.protocol_id = 1
        self.protocol = type("P", (), {"name": "CIDR+GnRH+PGF+GnRH"})()
        self.start_date = start_date
        self.status = status
        self.transfer_id = transfer_id
        self.logs = logs or []


def spec_protocol():
    """The protocol from the spec: Day 1/7/8/10/17 as zero-based offsets."""
    return [
        FakeStep(1, 0, "CIDR in + GnRH"),
        FakeStep(2, 6, "PGF2a #1"),
        FakeStep(3, 7, "CIDR out + PGF2a #2"),
        FakeStep(4, 9, "GnRH"),
        FakeStep(5, 16, "Embryo transfer", is_transfer_day=True),
    ]


class TestDueDates:
    def test_day_offset_zero_is_the_start_date(self):
        s = build_schedule(FakeEnrollment(TODAY), [FakeStep(1, 0, "Start")], TODAY)
        assert s.steps[0].due_date == TODAY

    def test_due_dates_are_start_plus_offset(self):
        start = date(2026, 8, 26)
        s = build_schedule(FakeEnrollment(start), spec_protocol(), TODAY)
        assert [x.due_date for x in s.steps] == [
            date(2026, 8, 26),
            date(2026, 9, 1),
            date(2026, 9, 2),
            date(2026, 9, 4),
            date(2026, 9, 11),
        ]

    def test_transfer_day_is_surfaced(self):
        s = build_schedule(FakeEnrollment(date(2026, 8, 26)), spec_protocol(), TODAY)
        assert s.transfer_due_date == date(2026, 9, 11)

    def test_negative_offsets_are_allowed(self):
        # Some programmes record a pre-treatment exam before day 0.
        s = build_schedule(FakeEnrollment(TODAY), [FakeStep(1, -3, "Pre-check")], TODAY)
        assert s.steps[0].due_date == TODAY - timedelta(days=3)
        assert s.steps[0].state == OVERDUE

    def test_steps_are_ordered_by_day(self):
        unordered = [FakeStep(1, 16, "Last"), FakeStep(2, 0, "First"), FakeStep(3, 6, "Middle")]
        s = build_schedule(FakeEnrollment(TODAY), unordered, TODAY)
        assert [x.step_name for x in s.steps] == ["First", "Middle", "Last"]


class TestStates:
    def test_past_unlogged_step_is_overdue(self):
        s = build_schedule(FakeEnrollment(TODAY - timedelta(days=5)), [FakeStep(1, 0, "X")], TODAY)
        assert s.steps[0].state == OVERDUE
        assert s.overdue_count == 1

    def test_step_due_today_is_not_overdue(self):
        s = build_schedule(FakeEnrollment(TODAY), [FakeStep(1, 0, "X")], TODAY)
        assert s.steps[0].state == DUE_TODAY
        assert s.overdue_count == 0

    def test_future_step_is_upcoming(self):
        s = build_schedule(FakeEnrollment(TODAY), [FakeStep(1, 5, "X")], TODAY)
        assert s.steps[0].state == UPCOMING

    def test_logged_step_is_done_even_when_late(self):
        # A treatment given late is still given; it must not stay flagged.
        enrollment = FakeEnrollment(
            TODAY - timedelta(days=10), logs=[FakeLog(1, TODAY - timedelta(days=8))]
        )
        s = build_schedule(enrollment, [FakeStep(1, 0, "X")], TODAY)
        assert s.steps[0].state == DONE
        assert s.steps[0].completed_on == TODAY - timedelta(days=8)
        assert s.overdue_count == 0

    def test_logs_without_a_step_id_are_ignored(self):
        # Free-text treatments predate the template and cannot close a step.
        enrollment = FakeEnrollment(TODAY - timedelta(days=5), logs=[FakeLog(None, TODAY)])
        s = build_schedule(enrollment, [FakeStep(1, 0, "X")], TODAY)
        assert s.steps[0].state == OVERDUE


class TestSummary:
    def test_next_step_is_the_earliest_pending(self):
        enrollment = FakeEnrollment(date(2026, 8, 26), logs=[FakeLog(1, date(2026, 8, 26))])
        s = build_schedule(enrollment, spec_protocol(), TODAY)
        assert s.next_step.step_name == "PGF2a #1"
        assert s.completed_count == 1
        assert s.total_steps == 5

    def test_all_done_reports_no_next_step(self):
        logs = [FakeLog(i, TODAY) for i in range(1, 6)]
        s = build_schedule(FakeEnrollment(date(2026, 8, 26), logs=logs), spec_protocol(), TODAY)
        assert s.next_step is None
        assert s.current_stage == "All steps recorded"

    def test_overdue_dominates_the_stage_label(self):
        s = build_schedule(FakeEnrollment(date(2026, 8, 26)), spec_protocol(), TODAY)
        assert "overdue" in s.current_stage

    def test_withdrawn_enrollment_reports_its_status(self):
        enrollment = FakeEnrollment(date(2026, 8, 26), status="Withdrawn")
        s = build_schedule(enrollment, spec_protocol(), TODAY)
        assert s.current_stage == "Withdrawn"

    def test_protocol_without_steps_says_so(self):
        s = build_schedule(FakeEnrollment(TODAY), [], TODAY)
        assert s.has_schedule is False
        assert s.total_steps == 0
        assert s.next_step is None
        assert "No schedule defined" in s.current_stage


@pytest.mark.parametrize(
    "offset,expected_state",
    [(-1, OVERDUE), (0, DUE_TODAY), (1, UPCOMING)],
)
def test_state_boundaries_around_today(offset, expected_state):
    s = build_schedule(FakeEnrollment(TODAY), [FakeStep(1, offset, "X")], TODAY)
    assert s.steps[0].state == expected_state
