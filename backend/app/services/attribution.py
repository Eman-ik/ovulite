"""Change attribution: detect step changes in an outcome rate and explain them.

The question this answers is "why did performance change?", which is different
from "what is performance?" (analytics) and "what will happen?" (prediction).
It is the question a programme director actually asks, and it is the one
Ovulite's data supports best.

Two independent pieces:

**Detection** — a changepoint scan over the pooled binomial counts. QC's
existing ``compute_cusum`` is deliberately not reused: it estimates a Gaussian
sigma from a series of equally-weighted observations, which is right for a lab
metric sampled at a steady rate and wrong here, where one month may carry 166
transfers and another 1. Weighting those equally would let a single-transfer
month move the chart as much as a whole season. This scan works on the counts,
so a month contributes in proportion to its denominator.

Significance comes from a permutation null rather than the scan statistic's
nominal p-value. Scanning every candidate split and reporting the best one is
a maximum over many correlated tests; its nominal p is badly optimistic. The
null here is "outcome is independent of when the transfer happened", generated
by shuffling outcomes across transfers while holding each period's size fixed.

**Attribution** — a Kitagawa (Oaxaca-Blinder) decomposition of the change into
a *mix* effect and a *rate* effect, for each grouping dimension:

    R = sum_g w_g * r_g          w_g = share of group g, r_g = its rate

    R1 - R0 = sum_g (w_g1 - w_g0) * mean(r_g)      <- mix: composition moved
            + sum_g mean(w_g) * (r_g1 - r_g0)      <- rate: performance moved

The symmetric weighting makes this decomposition exact: the two terms sum to
the observed change with no residual. That matters, because a decomposition
with a leftover term invites attributing the leftover to whatever the analyst
already believed.

This is the tool that catches the failure mode in `/research/protocols`: a
protocol adopted during a good month shows a large *mix* term and a near-zero
*rate* term, which is the signature of a composition shift rather than a
treatment effect.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

# Candidate splits need enough on both sides for a rate to mean anything.
MIN_SIDE_N = 25

# Permutation draws for the changepoint null. 400 gives a resolution of
# ~0.0025 on the p-value, which is finer than any decision made from it.
PERMUTATION_DRAWS = 400

# A dimension whose mix term accounts for at least this share of the total
# change is called out as a compositional explanation.
MIX_DOMINANCE_SHARE = 0.5

_RNG_SEED = 42


@dataclass
class Observation:
    """One transfer, reduced to what attribution needs."""

    period: str
    success: bool
    groups: dict[str, str]
    """Dimension name -> group label, e.g. {"protocol": "Natural heat"}."""


@dataclass
class GroupContribution:
    label: str
    share_before: float
    share_after: float
    rate_before_pct: float | None
    rate_after_pct: float | None
    n_before: int
    n_after: int
    mix_pp: float
    rate_pp: float
    only_in: str | None
    """"before" or "after" when the group is absent from the other period."""


@dataclass
class Decomposition:
    dimension: str
    mix_pp: float
    rate_pp: float
    mix_share: float
    """Absolute share of the change explained by composition, 0-1."""
    verdict: str
    groups: list[GroupContribution] = field(default_factory=list)


@dataclass
class ChangePoint:
    period: str
    """First period on the 'after' side."""
    n_before: int
    n_after: int
    rate_before_pct: float
    rate_after_pct: float
    delta_pp: float
    z_score: float
    permutation_p: float
    decompositions: list[Decomposition] = field(default_factory=list)
    summary: str = ""


# ── Detection ────────────────────────────────────────────


def _two_proportion_z(s1: int, n1: int, s0: int, n0: int) -> float:
    """Pooled two-proportion z. Returns 0 when the statistic is undefined."""
    if n1 == 0 or n0 == 0:
        return 0.0
    pooled = (s1 + s0) / (n1 + n0)
    if pooled <= 0 or pooled >= 1:
        return 0.0
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n0))
    return 0.0 if se == 0 else (s1 / n1 - s0 / n0) / se


def _ordered_periods(observations: list[Observation]) -> list[str]:
    return sorted({o.period for o in observations})


def _scan(
    flags: list[bool], boundaries: list[int]
) -> tuple[int | None, float]:
    """Return the boundary index maximising |z|, and that |z|.

    `flags` is the outcome sequence in period order; `boundaries` are the
    indices at which a period changes.
    """
    best_idx, best_z = None, 0.0
    total = len(flags)
    for idx in boundaries:
        if idx < MIN_SIDE_N or total - idx < MIN_SIDE_N:
            continue
        before, after = flags[:idx], flags[idx:]
        z = abs(_two_proportion_z(sum(after), len(after), sum(before), len(before)))
        if z > best_z:
            best_idx, best_z = idx, z
    return best_idx, best_z


def detect_change_point(observations: list[Observation]) -> tuple[int | None, float, float]:
    """Find the strongest step change and test it against a permutation null.

    Returns ``(split_index, |z|, permutation_p)``. The index is into the
    period-ordered observation list; everything from it onward is "after".
    """
    if len(observations) < 2 * MIN_SIDE_N:
        return (None, 0.0, 1.0)

    ordered = sorted(observations, key=lambda o: o.period)
    flags = [o.success for o in ordered]
    periods = [o.period for o in ordered]
    boundaries = [i for i in range(1, len(periods)) if periods[i] != periods[i - 1]]
    if not boundaries:
        return (None, 0.0, 1.0)

    split, observed_z = _scan(flags, boundaries)
    if split is None or observed_z == 0.0:
        return (None, 0.0, 1.0)

    # Null: outcome independent of period. Shuffling the outcome sequence
    # holds every period's size fixed and destroys only the time association.
    rng = random.Random(_RNG_SEED)
    shuffled = list(flags)
    at_least_as_extreme = 0
    for _ in range(PERMUTATION_DRAWS):
        rng.shuffle(shuffled)
        _, z = _scan(shuffled, boundaries)
        if z >= observed_z:
            at_least_as_extreme += 1
    p_value = (at_least_as_extreme + 1) / (PERMUTATION_DRAWS + 1)

    return (split, observed_z, p_value)


# ── Attribution ──────────────────────────────────────────


def decompose(
    before: list[Observation], after: list[Observation], dimension: str
) -> Decomposition:
    """Split the change in rate into composition and within-group performance.

    Groups present in only one period are attributed wholly to mix: their
    appearance or disappearance *is* a composition change, and no
    within-group comparison exists for them. Handled this way the
    decomposition stays exact.
    """
    n0, n1 = len(before), len(after)
    if n0 == 0 or n1 == 0:
        return Decomposition(dimension=dimension, mix_pp=0.0, rate_pp=0.0, mix_share=0.0,
                             verdict="Not enough data on one side of the change.")

    def tally(rows: list[Observation]) -> dict[str, list[int]]:
        out: dict[str, list[int]] = {}
        for o in rows:
            cell = out.setdefault(o.groups.get(dimension) or "Unrecorded", [0, 0])
            cell[0] += 1 if o.success else 0
            cell[1] += 1
        return out

    t0, t1 = tally(before), tally(after)
    contributions: list[GroupContribution] = []
    mix_total = rate_total = 0.0

    for label in sorted(set(t0) | set(t1)):
        s0, c0 = t0.get(label, (0, 0))
        s1, c1 = t1.get(label, (0, 0))
        w0, w1 = c0 / n0, c1 / n1
        r0 = s0 / c0 if c0 else None
        r1 = s1 / c1 if c1 else None

        if c0 and c1:
            mix = (w1 - w0) * ((r0 + r1) / 2)
            rate = ((w0 + w1) / 2) * (r1 - r0)
            only_in = None
        elif c1:
            # Appears only after: its whole contribution to R1 is compositional.
            mix, rate, only_in = w1 * r1, 0.0, "after"
        else:
            mix, rate, only_in = -w0 * r0, 0.0, "before"

        mix_total += mix
        rate_total += rate
        contributions.append(
            GroupContribution(
                label=label,
                share_before=round(w0 * 100, 1),
                share_after=round(w1 * 100, 1),
                rate_before_pct=None if r0 is None else round(r0 * 100, 1),
                rate_after_pct=None if r1 is None else round(r1 * 100, 1),
                n_before=c0,
                n_after=c1,
                mix_pp=round(mix * 100, 1),
                rate_pp=round(rate * 100, 1),
                only_in=only_in,
            )
        )

    mix_pp, rate_pp = mix_total * 100, rate_total * 100
    magnitude = abs(mix_pp) + abs(rate_pp)
    mix_share = 0.0 if magnitude == 0 else abs(mix_pp) / magnitude

    if magnitude < 1:
        verdict = f"{dimension.replace('_', ' ').title()} explains almost none of the change."
    elif mix_share >= MIX_DOMINANCE_SHARE:
        verdict = (
            f"Mostly a composition shift: the mix of {dimension.replace('_', ' ')} changed "
            f"({mix_pp:+.1f} pp), rather than any group performing differently ({rate_pp:+.1f} pp)."
        )
    else:
        verdict = (
            f"Mostly a genuine change within groups ({rate_pp:+.1f} pp); the mix of "
            f"{dimension.replace('_', ' ')} barely moved ({mix_pp:+.1f} pp)."
        )

    contributions.sort(key=lambda c: -(abs(c.mix_pp) + abs(c.rate_pp)))
    return Decomposition(
        dimension=dimension,
        mix_pp=round(mix_pp, 1),
        rate_pp=round(rate_pp, 1),
        mix_share=round(mix_share, 2),
        verdict=verdict,
        groups=contributions,
    )


def _summarise(change: ChangePoint) -> str:
    """One paragraph a programme director can act on."""
    direction = "rose" if change.delta_pp > 0 else "fell"
    parts = [
        f"Pregnancy rate {direction} {abs(change.delta_pp):.1f} pp at {change.period} "
        f"({change.rate_before_pct}% over {change.n_before} transfers → "
        f"{change.rate_after_pct}% over {change.n_after}), "
        f"permutation p={change.permutation_p:.3f}."
    ]

    explained = [d for d in change.decompositions if abs(d.mix_pp) >= 1.0]
    if explained:
        top = max(explained, key=lambda d: abs(d.mix_pp))
        parts.append(
            f"The largest compositional contribution is {top.dimension.replace('_', ' ')} "
            f"at {top.mix_pp:+.1f} pp."
        )
    else:
        parts.append("No dimension's composition explains more than 1 pp of it.")

    within = [d for d in change.decompositions if abs(d.rate_pp) >= abs(change.delta_pp) * 0.7]
    if within:
        names = ", ".join(d.dimension.replace("_", " ") for d in within)
        parts.append(
            f"The change persists within {names}, so it is a broad shift in practice or "
            "conditions rather than a change in what was being transferred. "
            "Look for what changed operationally at this point."
        )
    return " ".join(parts)


def analyse(observations: list[Observation], dimensions: list[str]) -> ChangePoint | None:
    """Detect the strongest change point and attribute it across dimensions."""
    split, z, p_value = detect_change_point(observations)
    if split is None:
        return None

    ordered = sorted(observations, key=lambda o: o.period)
    before, after = ordered[:split], ordered[split:]
    r0 = sum(o.success for o in before) / len(before) * 100
    r1 = sum(o.success for o in after) / len(after) * 100

    change = ChangePoint(
        period=after[0].period,
        n_before=len(before),
        n_after=len(after),
        rate_before_pct=round(r0, 1),
        rate_after_pct=round(r1, 1),
        delta_pp=round(r1 - r0, 1),
        z_score=round(z, 2),
        permutation_p=round(p_value, 4),
        decompositions=[decompose(before, after, d) for d in dimensions],
    )
    change.summary = _summarise(change)
    return change
