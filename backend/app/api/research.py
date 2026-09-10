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
"""

import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.api.transfers import _clean_pregnancy_result
from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.et_transfer import ETTransfer
from app.models.user import User
from app.schemas.research import (
    DonorSireCell,
    DonorSireResponse,
    FactorLevel,
    OutcomeFactor,
    OutcomeFactorsResponse,
    ProtocolComparisonResponse,
    ProtocolComparisonRow,
    RateCell,
)

router = APIRouter()

# Below this, a proportion is reported as null rather than as a percentage.
# Five is the same guard the dashboard's performance panel uses.
MIN_SAMPLE_SIZE = 5


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
            joinedload(ETTransfer.embryo),
            joinedload(ETTransfer.protocol),
        )
        .filter(ETTransfer.organization_id == org_id)
        .filter(ETTransfer.pc1_result.isnot(None))
        .all()
    )
    return [t for t in transfers if _clean_pregnancy_result(t.pc1_result) in ("Pregnant", "Open")]


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

    rows: list[ProtocolComparisonRow] = []
    for protocol_id, group in groups.items():
        n = len(group)
        successes = sum(1 for t in group if _is_pregnant(t))
        is_baseline = protocol_id == baseline_id
        p_value = None if is_baseline else two_proportion_p_value(successes, n, base_s, base_n)
        diff = None
        if not is_baseline and n and base_n:
            diff = round((successes / n - base_s / base_n) * 100, 1)
        rows.append(
            ProtocolComparisonRow(
                protocol_id=protocol_id,
                protocol_name=protocol_names.get(protocol_id, f"Protocol {protocol_id}"),
                is_baseline=is_baseline,
                diff_vs_baseline_pp=diff,
                p_value=None if p_value is None else round(p_value, 4),
                significant_at_05=None if p_value is None else p_value < 0.05,
                **_rate_cell(successes, n),
            )
        )

    rows.sort(key=lambda r: -r.n)
    return ProtocolComparisonResponse(
        min_sample_size=MIN_SAMPLE_SIZE,
        baseline_protocol=protocol_names.get(baseline_id),
        rows=rows,
        note=(
            "Two-proportion z-tests against the largest protocol, uncorrected for "
            f"multiple comparisons — {len(rows) - 1} tests were run, so a single p < 0.05 "
            "is weak evidence on its own. Intervals are Wilson score intervals. "
            "These are observational groups, not randomised arms: protocol choice "
            "may correlate with recipient condition and season."
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
