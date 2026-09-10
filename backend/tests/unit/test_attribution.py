"""Tests for the change-attribution service.

The property that matters most is exactness: mix + rate must equal the observed
change with no residual. A decomposition that leaves a remainder invites
attributing the remainder to whatever the analyst already believed, so it is
asserted on every shape of input including the awkward ones.
"""

import random

import pytest

from app.services.attribution import (
    Observation,
    analyse,
    decompose,
    detect_change_point,
)


def make(period: str, group: str, success: bool) -> Observation:
    return Observation(period=period, success=success, groups={"d": group})


def observed_delta_pp(before: list[Observation], after: list[Observation]) -> float:
    r0 = sum(o.success for o in before) / len(before)
    r1 = sum(o.success for o in after) / len(after)
    return (r1 - r0) * 100


class TestDecompositionIsExact:
    """mix + rate == observed change, for every input shape."""

    def test_pure_composition_shift(self):
        # Identical within-group rates; only the mix moves.
        before = [make("P0", "A", i < 20) for i in range(100)] + [make("P0", "B", i < 12) for i in range(20)]
        after = [make("P1", "A", i < 4) for i in range(20)] + [make("P1", "B", i < 60) for i in range(100)]
        d = decompose(before, after, "d")
        assert d.mix_pp + d.rate_pp == pytest.approx(observed_delta_pp(before, after), abs=0.15)
        # Rates held constant, so the change must be attributed to mix.
        assert d.rate_pp == pytest.approx(0.0, abs=0.15)
        assert d.mix_share > 0.9

    def test_pure_rate_shift(self):
        # Identical composition; every group improves.
        before = [make("P0", "A", i < 20) for i in range(100)] + [make("P0", "B", i < 30) for i in range(100)]
        after = [make("P1", "A", i < 50) for i in range(100)] + [make("P1", "B", i < 60) for i in range(100)]
        d = decompose(before, after, "d")
        assert d.mix_pp + d.rate_pp == pytest.approx(observed_delta_pp(before, after), abs=0.15)
        assert d.mix_pp == pytest.approx(0.0, abs=0.15)
        assert d.mix_share < 0.1

    def test_group_appearing_only_after_is_attributed_to_mix(self):
        # This is the /research/protocols situation: a protocol introduced
        # partway through has no before-rate to compare against, so its whole
        # contribution is compositional and the rate term must stay zero.
        before = [make("P0", "old", i < 40) for i in range(160)]
        after = [make("P1", "old", i < 20) for i in range(60)] + [make("P1", "new", i < 42) for i in range(100)]
        d = decompose(before, after, "d")
        assert d.mix_pp + d.rate_pp == pytest.approx(observed_delta_pp(before, after), abs=0.15)
        new = next(g for g in d.groups if g.label == "new")
        assert new.only_in == "after"
        assert new.rate_pp == 0.0
        assert new.rate_before_pct is None

    def test_group_disappearing_is_attributed_to_mix(self):
        before = [make("P0", "keep", i < 30) for i in range(100)] + [make("P0", "drop", i < 5) for i in range(50)]
        after = [make("P1", "keep", i < 30) for i in range(100)]
        d = decompose(before, after, "d")
        assert d.mix_pp + d.rate_pp == pytest.approx(observed_delta_pp(before, after), abs=0.15)
        dropped = next(g for g in d.groups if g.label == "drop")
        assert dropped.only_in == "before"
        assert dropped.rate_pp == 0.0

    def test_exact_on_random_inputs(self):
        rng = random.Random(11)
        for _ in range(25):
            labels = ["A", "B", "C", "D"]
            before = [
                make("P0", rng.choice(labels), rng.random() < rng.uniform(0.1, 0.7)) for _ in range(rng.randint(40, 200))
            ]
            after = [
                make("P1", rng.choice(labels), rng.random() < rng.uniform(0.1, 0.7)) for _ in range(rng.randint(40, 200))
            ]
            d = decompose(before, after, "d")
            # Tolerance covers only the per-group rounding to 1 decimal place.
            assert d.mix_pp + d.rate_pp == pytest.approx(observed_delta_pp(before, after), abs=0.3)

    def test_unrecorded_values_become_their_own_group(self):
        before = [Observation("P0", i < 10, {"d": None}) for i in range(40)]
        after = [Observation("P1", i < 30, {"d": None}) for i in range(40)]
        d = decompose(before, after, "d")
        assert [g.label for g in d.groups] == ["Unrecorded"]
        assert d.mix_pp + d.rate_pp == pytest.approx(observed_delta_pp(before, after), abs=0.15)


class TestDetection:
    def test_finds_a_planted_step_change(self):
        before = [make("2025-01", "A", i < 20) for i in range(100)]
        after = [make("2025-02", "A", i < 60) for i in range(100)]
        split, z, p = detect_change_point(before + after)
        assert split == 100
        assert z > 3
        assert p < 0.05

    def test_no_change_in_stationary_data(self):
        rng = random.Random(3)
        obs = [make(f"2025-{m:02d}", "A", rng.random() < 0.3) for m in range(1, 9) for _ in range(40)]
        _, _, p = detect_change_point(obs)
        # Stationary data should not clear the permutation threshold.
        assert p > 0.05

    def test_returns_nothing_when_too_small(self):
        split, z, p = detect_change_point([make("2025-01", "A", True) for _ in range(10)])
        assert split is None
        assert p == 1.0

    def test_analyse_returns_none_without_a_change_point(self):
        assert analyse([make("2025-01", "A", True) for _ in range(10)], ["d"]) is None
