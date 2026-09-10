"""Tests for the vet workflow's derived state.

The pc1 mirror is the risky part: `et_transfers.pc1_result` is read by the
dashboard, the research surface, the analytics pipeline and the ML feature
builder, so a sync bug there is silent and wide-reaching. These tests pin the
two behaviours that matter — it tracks the earliest check, and it never
destroys a legacy result the new table does not hold.
"""

from datetime import date

import pytest

from app.api.vet import PLAUSIBLE_CHECK_WINDOW, RETENTION_STAGES


class _Check:
    def __init__(self, check_date, result):
        self.check_date = check_date
        self.result = result


class _Transfer:
    def __init__(self, pc1_date=None, pc1_result=None):
        self.transfer_id = 1
        self.pc1_date = pc1_date
        self.pc1_result = pc1_result


class _Query:
    def __init__(self, earliest):
        self._earliest = earliest

    def filter(self, *_):
        return self

    def order_by(self, *_):
        return self

    def first(self):
        return self._earliest


class _Session:
    def __init__(self, earliest):
        self._earliest = earliest

    def query(self, _model):
        return _Query(self._earliest)


def sync(transfer, earliest):
    from app.api.vet import _sync_pc1

    _sync_pc1(_Session(earliest), transfer)
    return transfer


class TestPc1Mirror:
    def test_mirrors_the_earliest_check(self):
        t = sync(_Transfer(), _Check(date(2026, 3, 20), "Pregnant"))
        assert t.pc1_date == date(2026, 3, 20)
        assert t.pc1_result == "Pregnant"

    def test_lost_maps_to_open_for_legacy_readers(self):
        # "Lost" is not in the legacy vocabulary; writing it through would make
        # _clean_pregnancy_result return None and drop the row from every rate.
        t = sync(_Transfer(), _Check(date(2026, 4, 6), "Lost"))
        assert t.pc1_result == "Open"

    def test_no_checks_preserves_a_legacy_result(self):
        # 180 rows in the production dataset carry a pc1_result with no
        # pc1_date, so migration 013 could not backfill them. Nulling here
        # would destroy those results the first time a check was added and
        # then deleted.
        t = sync(_Transfer(pc1_date=None, pc1_result="Pregnant"), None)
        assert t.pc1_result == "Pregnant"

    def test_no_checks_does_not_invent_a_result(self):
        t = sync(_Transfer(), None)
        assert t.pc1_result is None


class TestConfiguration:
    def test_retention_stages_do_not_overlap_and_are_ordered(self):
        bounds = [(low, high) for _, low, high in RETENTION_STAGES]
        for (_, high), (low, _) in zip(bounds, bounds[1:]):
            assert low == high + 1, "stage windows must be contiguous with no gap or overlap"

    def test_plausible_window_covers_every_retention_stage(self):
        low, high = PLAUSIBLE_CHECK_WINDOW
        assert low <= RETENTION_STAGES[0][1]
        assert high >= RETENTION_STAGES[-1][2], (
            "a check inside a retention stage must not be flagged implausible"
        )


@pytest.mark.parametrize(
    "offset,expected",
    [(-305, True), (-1, True), (0, False), (28, False), (120, False), (121, True), (340, True)],
)
def test_implausible_offset_boundaries(offset, expected):
    low, high = PLAUSIBLE_CHECK_WINDOW
    assert (not (low <= offset <= high)) is expected
