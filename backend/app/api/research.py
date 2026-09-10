"""Comparative outcome analyses for the researcher/data-analyst role.

These are live queries against the transactional tables, deliberately separate
from `analytics.py` — that module serves pre-generated pipeline artifacts and
has no filter support. Everything here is computed on request so a researcher
can slice it.

Statistical discipline, applied consistently:

* Every rate ships with its denominator. A rate without an ``n`` is not
  interpretable and this dataset is small enough that it matters.
* Groups below ``MIN_SAMPLE_SIZE`` return ``rate_pct = None`` with
  ``insufficient_data = True`` instead of a 0%/100% that reads as a finding.
* Intervals are Wilson score intervals, not normal-approximation — the normal
  approximation is unreliable at these group sizes and degenerates badly near
  0 and 1.
* Significance is an uncorrected two-proportion z-test against the largest
  protocol. With five protocols that is five comparisons, so a single p < 0.05
  is weak evidence; the response says so in its ``note``.
* **Group comparisons are stratified by month.** Practices are adopted at a
  point in time, so a protocol introduced during a good period inherits that
  period's outcomes. This dataset demonstrates it: pooled, the December-2025
  protocol looks +14.8 pp better than the baseline at p=0.005, but within
  December the baseline actually scored higher (46.2% vs 42.0%) — the whole
  programme roughly doubled that month regardless of protocol. Reporting only
  the pooled figure would assert a treatment effect that the data contradicts,
  so every group comparison carries a Mantel-Haenszel estimate alongside it
  and is flagged when the two disagree.
"""

import math
from dataclasses import asdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.api.transfers import _clean_pregnancy_result
from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.embryo import Embryo
from app.models.et_transfer import ETTransfer
from app.models.user import User
from app.services.attribution import Observation, analyse
from app.schemas.research import (
    AttributionResponse,
    ChangePointOut,
    DonorSireCell,
    DonorSireResponse,
    FactorLevel,
    OutcomeFactor,
    OutcomeFactorsResponse,
    PeriodRate,
    ProtocolComparisonResponse,
    ProtocolComparisonRow,
    RateCell,
)

router = APIRouter()

# Below this, a proportion is reported as null rather than as a percentage.
# Five is the same guard the dashboard's performance panel uses.
MIN_SAMPLE_SIZE = 5

# A pooled and a time-adjusted estimate that differ by at least this many
# percentage points describe materially different conclusions, so the pooled
# one is flagged rather than shown on its own.
CONFOUND_SHIFT_PP = 5.0

# Below this share of a group's transfers falling in months the baseline was
# also used, group and period cannot be told apart with any confidence.
MIN_TIME_OVERLAP_PCT = 60.0


# ── Statistics ───────────────────────────────────────────


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion, as percentages.

    Preferred over the normal approximation because it stays inside [0, 1] and
    remains sensible for the small, lopsided groups this dataset produces.
    """
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (max(0.0, (centre - margin)) * 100, min(1.0, (centre + margin)) * 100)


def two_proportion_p_value(s1: int, n1: int, s2: int, n2: int) -> float | None:
    """Two-sided p-value for H0: p1 == p2, via the pooled z-test.

    Returns None when either group is empty or the pooled proportion is
    degenerate (0 or 1), where the test statistic is undefined.
    """
    if n1 == 0 or n2 == 0:
        return None
    pooled = (s1 + s2) / (n1 + n2)
    if pooled in (0.0, 1.0):
        return None
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return None
    z = (s1 / n1 - s2 / n2) / se
    # Two-sided normal tail via the error function.
    return math.erfc(abs(z) / math.sqrt(2))


def chi2_sf_1df(x: float) -> float:
    """Upper-tail probability of a chi-square with 1 degree of freedom.

    For 1 df the statistic is Z², so P(X > x) = P(|Z| > √x) = erfc(√(x/2)).
    """
    return math.erfc(math.sqrt(x / 2))


def mantel_haenszel(strata: list[tuple[int, int, int, int]]) -> tuple[float | None, float | None]:
    """Pool a 2×2 comparison across strata, controlling for the stratum variable.

    Each stratum is ``(a, n1, b, n0)`` — successes and totals for the exposed
    group (a/n1) and the reference group (b/n0). Returns the MH risk
    difference as percentage points and the Cochran-Mantel-Haenszel p-value.

    This is the correction for confounding by the stratum variable: comparing
    like with like inside each stratum, then pooling with weights, instead of
    collapsing the table and letting stratum composition drive the result.
    """
    usable = [(a, n1, b, n0) for a, n1, b, n0 in strata if n1 > 0 and n0 > 0]
    if not usable:
        return (None, None)

    # MH weights for a risk difference: w = n1*n0 / (n1+n0).
    num = den = 0.0
    for a, n1, b, n0 in usable:
        w = n1 * n0 / (n1 + n0)
        num += w * (a / n1 - b / n0)
        den += w
    diff = None if den == 0 else (num / den) * 100

    # CMH statistic, with the continuity correction omitted (it is
    # conservative and these strata are not tiny).
    obs = sum(a for a, _, _, _ in usable)
    exp = var = 0.0
    for a, n1, b, n0 in usable:
        total = n1 + n0
        successes = a + b
        if total < 2:
            continue
        exp += n1 * successes / total
        var += n1 * n0 * successes * (total - successes) / (total**2 * (total - 1))
    p_value = None if var <= 0 else chi2_sf_1df((obs - exp) ** 2 / var)

    return (None if diff is None else round(diff, 1), None if p_value is None else round(p_value, 4))


def _rate_cell(successes: int, n: int) -> dict:
    """Build the shared RateCell fields, applying the sample-size guard."""
    if n < MIN_SAMPLE_SIZE:
        return {
            "n": n,
            "successes": successes,
            "rate_pct": None,
            "ci_low_pct": None,
            "ci_high_pct": None,
            "insufficient_data": True,
        }
    low, high = wilson_interval(successes, n)
    return {
        "n": n,
        "successes": successes,
        "rate_pct": round(successes / n * 100, 1),
        "ci_low_pct": round(low, 1),
        "ci_high_pct": round(high, 1),
        "insufficient_data": False,
    }


# ── Shared query ─────────────────────────────────────────


def _resolved_transfers(db: Session, org_id: int) -> list[ETTransfer]:
    """Transfers with a usable PC1 outcome, with their joins preloaded.

    Rows whose raw pc1_result does not normalize to Pregnant/Open are dropped:
    they carry no outcome information, and counting them in a denominator
    would silently deflate every rate on this page.
    """
    transfers = (
        db.query(ETTransfer)
        .options(
            joinedload(ETTransfer.embryo).joinedload(Embryo.donor),
            joinedload(ETTransfer.embryo).joinedload(Embryo.sire),
            joinedload(ETTransfer.protocol),
            joinedload(ETTransfer.technician),
        )
        .filter(ETTransfer.organization_id == org_id)
        .filter(ETTransfer.pc1_result.isnot(None))
        .all()
    )
    return [t for t in transfers if _clean_pregnancy_result(t.pc1_result) in ("Pregnant", "Open")]


def _stratum(t: ETTransfer) -> str:
    """Month key used to stratify comparisons, so period cannot masquerade as
    a treatment effect. Month is the finest bucket this dataset supports."""
    return t.et_date.strftime("%Y-%m") if t.et_date else "unknown"


def _is_pregnant(t: ETTransfer) -> bool:
    return _clean_pregnancy_result(t.pc1_result) == "Pregnant"


def _overall(transfers: list[ETTransfer]) -> RateCell:
    return RateCell(**_rate_cell(sum(1 for t in transfers if _is_pregnant(t)), len(transfers)))


# ── Donor × Sire ─────────────────────────────────────────


@router.get("/donor-sire", response_model=DonorSireResponse)
def donor_sire_matrix(
    min_n: int = Query(MIN_SAMPLE_SIZE, ge=1, le=100),
    limit_donors: int = Query(12, ge=1, le=50),
    limit_sires: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DonorSireResponse:
    """Pregnancy rate for each donor × sire combination.

    Restricted to the busiest donors and sires so the matrix stays readable;
    a combination that clears `min_n` is reported with its interval, and one
    that does not is returned with a null rate so the frontend can render the
    cell as "too few" rather than as a number.
    """
    transfers = _resolved_transfers(db, current_user.organization_id)

    pairs: dict[tuple[int, int], list[ETTransfer]] = {}
    donor_totals: dict[int, int] = {}
    sire_totals: dict[int, int] = {}
    names: dict[str, str] = {}

    for t in transfers:
        e = t.embryo
        if e is None or e.donor_id is None or e.sire_id is None:
            continue
        pairs.setdefault((e.donor_id, e.sire_id), []).append(t)
        donor_totals[e.donor_id] = donor_totals.get(e.donor_id, 0) + 1
        sire_totals[e.sire_id] = sire_totals.get(e.sire_id, 0) + 1
        if e.donor:
            names[f"d{e.donor_id}"] = e.donor.tag_id
        if e.sire:
            names[f"s{e.sire_id}"] = e.sire.name

    top_donors = sorted(donor_totals, key=lambda k: donor_totals[k], reverse=True)[:limit_donors]
    top_sires = sorted(sire_totals, key=lambda k: sire_totals[k], reverse=True)[:limit_sires]
    donor_set, sire_set = set(top_donors), set(top_sires)

    cells: list[DonorSireCell] = []
    for (donor_id, sire_id), rows in pairs.items():
        if donor_id not in donor_set or sire_id not in sire_set:
            continue
        base = _rate_cell(sum(1 for t in rows if _is_pregnant(t)), len(rows))
        if base["n"] < min_n:
            base |= {"rate_pct": None, "ci_low_pct": None, "ci_high_pct": None, "insufficient_data": True}
        cells.append(
            DonorSireCell(
                donor_id=donor_id,
                donor_tag=names.get(f"d{donor_id}", str(donor_id)),
                sire_id=sire_id,
                sire_name=names.get(f"s{sire_id}", str(sire_id)),
                **base,
            )
        )

    cells.sort(key=lambda c: (-c.n, c.donor_tag))
    return DonorSireResponse(
        min_sample_size=min_n,
        donors=[names.get(f"d{d}", str(d)) for d in top_donors],
        sires=[names.get(f"s{s}", str(s)) for s in top_sires],
        cells=cells,
        overall=_overall(transfers),
        note=(
            "Pregnancy rate at PC1 for each donor × sire pair, over the busiest "
            f"{len(top_donors)} donors and {len(top_sires)} sires. Pairs with fewer than "
            f"{min_n} transfers show no rate. Blastocyst rate per pair is not available: "
            "every oocyte and cleavage count in ivf_batches is null in this dataset."
        ),
    )


# ── Protocols ────────────────────────────────────────────


@router.get("/protocols", response_model=ProtocolComparisonResponse)
def protocol_comparison(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProtocolComparisonResponse:
    """Pregnancy rate per synchronization protocol, tested against the largest.

    The protocol with the most transfers is the baseline rather than the
    best-performing one: comparing every arm against the observed maximum
    would bias the comparison toward significance.
    """
    transfers = _resolved_transfers(db, current_user.organization_id)

    groups: dict[int, list[ETTransfer]] = {}
    protocol_names: dict[int, str] = {}
    for t in transfers:
        if t.protocol_id is None:
            continue
        groups.setdefault(t.protocol_id, []).append(t)
        if t.protocol:
            protocol_names[t.protocol_id] = t.protocol.name

    if not groups:
        return ProtocolComparisonResponse(
            min_sample_size=MIN_SAMPLE_SIZE,
            baseline_protocol=None,
            rows=[],
            note="No transfers with both a protocol and a resolved outcome.",
        )

    baseline_id = max(groups, key=lambda k: len(groups[k]))
    base_rows = groups[baseline_id]
    base_n, base_s = len(base_rows), sum(1 for t in base_rows if _is_pregnant(t))

    # Counts per (protocol, month), the stratification used below.
    by_stratum: dict[tuple[int, str], list[int]] = {}
    for protocol_id, group in groups.items():
        for t in group:
            key = (protocol_id, _stratum(t))
            cell = by_stratum.setdefault(key, [0, 0])
            cell[0] += 1 if _is_pregnant(t) else 0
            cell[1] += 1
    all_months = sorted({m for _, m in by_stratum})

    rows: list[ProtocolComparisonRow] = []
    for protocol_id, group in groups.items():
        n = len(group)
        successes = sum(1 for t in group if _is_pregnant(t))
        is_baseline = protocol_id == baseline_id

        p_value = None if is_baseline else two_proportion_p_value(successes, n, base_s, base_n)
        diff = None
        if not is_baseline and n and base_n:
            diff = round((successes / n - base_s / base_n) * 100, 1)

        adj_diff = adj_p = overlap_pct = None
        strata_compared = 0
        confounded = False
        reason: str | None = None

        if not is_baseline:
            strata = []
            overlapping_n = 0
            for month in all_months:
                a, n1 = by_stratum.get((protocol_id, month), [0, 0])
                b, n0 = by_stratum.get((baseline_id, month), [0, 0])
                if n1 > 0 and n0 > 0:
                    strata.append((a, n1, b, n0))
                    overlapping_n += n1
            strata_compared = len(strata)
            overlap_pct = round(overlapping_n / n * 100, 1) if n else None
            adj_diff, adj_p = mantel_haenszel(strata)

            # Two independent ways the pooled number can mislead.
            if not strata:
                confounded = True
                reason = (
                    "This protocol was never used in the same month as the baseline, so its "
                    "pooled difference measures the period it was used in, not the protocol. "
                    "No adjustment is possible."
                )
            elif adj_diff is not None and diff is not None:
                flipped = (adj_diff > 0) != (diff > 0) and abs(adj_diff - diff) > 1
                shifted = abs(adj_diff - diff) >= CONFOUND_SHIFT_PP
                if flipped or shifted:
                    confounded = True
                    reason = (
                        f"Pooled difference is {diff:+.1f} pp but {adj_diff:+.1f} pp once compared "
                        f"within the same months. The pooled figure is largely a period effect, "
                        f"not a protocol effect."
                    )
                elif overlap_pct is not None and overlap_pct < MIN_TIME_OVERLAP_PCT:
                    confounded = True
                    reason = (
                        f"Only {overlap_pct}% of this protocol's transfers fall in months the "
                        "baseline was also used, so protocol and period are hard to separate."
                    )

        rows.append(
            ProtocolComparisonRow(
                protocol_id=protocol_id,
                protocol_name=protocol_names.get(protocol_id, f"Protocol {protocol_id}"),
                is_baseline=is_baseline,
                diff_vs_baseline_pp=diff,
                p_value=None if p_value is None else round(p_value, 4),
                significant_at_05=None if p_value is None else p_value < 0.05,
                adjusted_diff_pp=adj_diff,
                adjusted_p_value=adj_p,
                adjusted_significant_at_05=None if adj_p is None else adj_p < 0.05,
                strata_compared=strata_compared,
                time_overlap_pct=overlap_pct,
                confounded=confounded,
                confound_reason=reason,
                **_rate_cell(successes, n),
            )
        )

    rows.sort(key=lambda r: -r.n)

    # Per-month outcome rate, so a reader can see a period effect directly
    # instead of having to take the adjustment on trust.
    month_totals: dict[str, list[int]] = {}
    for t in transfers:
        cell = month_totals.setdefault(_stratum(t), [0, 0])
        cell[0] += 1 if _is_pregnant(t) else 0
        cell[1] += 1
    period_rates = [
        PeriodRate(period=month, **_rate_cell(s, n))
        for month, (s, n) in sorted(month_totals.items())
    ]

    confounding_detected = any(r.confounded for r in rows)
    warning = None
    if confounding_detected:
        names = [r.protocol_name for r in rows if r.confounded]
        warning = (
            f"Protocol usage is not evenly spread over time, so the pooled comparison is "
            f"confounded by period for: {', '.join(names)}. Read the time-adjusted column, "
            "not the pooled one."
        )

    return ProtocolComparisonResponse(
        min_sample_size=MIN_SAMPLE_SIZE,
        baseline_protocol=protocol_names.get(baseline_id),
        rows=rows,
        confounding_detected=confounding_detected,
        warning=warning,
        period_rates=period_rates,
        note=(
            "Pooled columns compare raw totals and ignore when each protocol was used. "
            "The adjusted column is a Mantel-Haenszel risk difference stratified by month, "
            "which compares protocols only within months where both were used. Where the two "
            "disagree, the pooled figure is picking up the period rather than the protocol. "
            f"Tests are uncorrected across {len(rows) - 1} comparisons. These are observational "
            "groups, not randomised arms: stratifying by month removes the period effect but "
            "not selection on recipient condition."
        ),
    )


# ── Outcome factors ──────────────────────────────────────


@router.get("/outcome-factors", response_model=OutcomeFactorsResponse)
def outcome_factors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OutcomeFactorsResponse:
    """Pregnancy rate broken down by each embryo attribute that varies.

    A factor with no variation is returned with ``available = False`` and the
    reason, rather than omitted — an absent breakdown is otherwise
    indistinguishable from one that was never asked for.
    """
    transfers = _resolved_transfers(db, current_user.organization_id)

    def breakdown(key: str, label: str, extract, fmt) -> OutcomeFactor:
        buckets: dict[object, list[ETTransfer]] = {}
        for t in transfers:
            value = extract(t)
            if value is None:
                continue
            buckets.setdefault(value, []).append(t)

        if len(buckets) < 2:
            only = next(iter(buckets), None)
            reason = (
                f"Every embryo in this dataset has the same value ({fmt(only)}), "
                "so there is nothing to compare."
                if buckets
                else "No transfers carry this field."
            )
            return OutcomeFactor(key=key, label=label, levels=[], available=False, unavailable_reason=reason)

        levels = [
            FactorLevel(label=fmt(value), **_rate_cell(sum(1 for t in rows if _is_pregnant(t)), len(rows)))
            for value, rows in sorted(buckets.items(), key=lambda kv: str(kv[0]))
        ]
        return OutcomeFactor(key=key, label=label, levels=levels, available=True, unavailable_reason=None)

    factors = [
        breakdown(
            "embryo_stage",
            "Embryo Stage at Transfer",
            lambda t: t.embryo.stage if t.embryo else None,
            lambda v: f"Stage {v}",
        ),
        breakdown(
            "embryo_grade",
            "Embryo Grade",
            lambda t: t.embryo.grade if t.embryo else None,
            lambda v: f"Grade {v}",
        ),
        breakdown(
            "fresh_or_frozen",
            "Fresh vs Frozen",
            lambda t: t.embryo.fresh_or_frozen if t.embryo else None,
            lambda v: str(v),
        ),
        breakdown(
            "cl_side",
            "Corpus Luteum Side",
            lambda t: t.cl_side,
            lambda v: str(v),
        ),
    ]

    return OutcomeFactorsResponse(
        min_sample_size=MIN_SAMPLE_SIZE,
        factors=factors,
        overall=_overall(transfers),
    )


# ── Change attribution ───────────────────────────────────

# Dimensions worth decomposing over: each is recorded per transfer and could
# plausibly shift in composition between periods. Ordered most to least likely
# to be the operational lever.
ATTRIBUTION_DIMENSIONS = [
    "protocol",
    "farm",
    "technician",
    "donor_breed",
    "fresh_or_frozen",
    "embryo_stage",
    "cl_side",
]


@router.get("/attribution", response_model=AttributionResponse)
def change_attribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttributionResponse:
    """Detect the strongest step change in pregnancy rate and explain it.

    Answers "why did performance change?" rather than "what is performance?".
    Each dimension's contribution is split into a composition (mix) effect and
    a within-group (rate) effect, so a shift caused by *what* was transferred
    is never reported as a change in *how well* it was done.
    """
    transfers = _resolved_transfers(db, current_user.organization_id)

    observations = [
        Observation(
            period=_stratum(t),
            success=_is_pregnant(t),
            groups={
                "protocol": t.protocol.name if t.protocol else None,
                "farm": t.farm_location,
                "technician": t.technician.name if t.technician else None,
                "donor_breed": t.embryo.donor.breed if t.embryo and t.embryo.donor else None,
                "fresh_or_frozen": t.embryo.fresh_or_frozen if t.embryo else None,
                "embryo_stage": (
                    f"Stage {t.embryo.stage}" if t.embryo and t.embryo.stage is not None else None
                ),
                "cl_side": t.cl_side,
            },
        )
        for t in transfers
    ]

    change = analyse(observations, ATTRIBUTION_DIMENSIONS)

    month_totals: dict[str, list[int]] = {}
    for t in transfers:
        cell = month_totals.setdefault(_stratum(t), [0, 0])
        cell[0] += 1 if _is_pregnant(t) else 0
        cell[1] += 1
    series = [
        PeriodRate(period=month, **_rate_cell(s, n)) for month, (s, n) in sorted(month_totals.items())
    ]

    return AttributionResponse(
        change_point=None if change is None else ChangePointOut(**asdict(change)),
        series=series,
        dimensions_tested=ATTRIBUTION_DIMENSIONS,
        note=(
            "Mix (pp) is how much of the change came from the population shifting; rate (pp) is "
            "how much came from groups themselves performing differently. The two are an exact "
            "decomposition of the observed change — they sum to it with no residual. A large mix "
            "term means the comparison you were about to make is confounded. A large rate term "
            "spread across every dimension means something changed in practice or conditions that "
            "is not recorded in the data, and is worth asking the team about. Significance is a "
            "permutation p-value, because scanning every candidate split and reporting the best "
            "one makes the nominal p-value far too generous."
        ),
    )
