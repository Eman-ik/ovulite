"""Synthetic anomaly injection for QC testing (ROADMAP task 4.4).

Generates fake batches with known anomalies to verify the detection pipeline.
Anomaly types:
- Technician with drastically low pregnancy rate
- Sudden CL measurement shift (calibration drift)
- Unusual embryo grade distribution
- High-volume outlier batch
"""

import logging

import numpy as np
import pandas as pd

from .config import SEED

logger = logging.getLogger(__name__)


def inject_synthetic_anomalies(
    df: pd.DataFrame,
    n_anomalous_batches: int = 5,
    seed: int = SEED,
) -> tuple[pd.DataFrame, list[dict]]:
    """Inject synthetic anomalous records into the dataset.

    Parameters
    ----------
    df : Clean ET data (from load_et_data)
    n_anomalous_batches : Number of anomalous batches to inject
    seed : Random seed

    Returns
    -------
    augmented_df : Original + synthetic records
    ground_truth : List of dicts describing each injected anomaly
    """
    rng = np.random.RandomState(seed)
    synthetic_rows = []
    ground_truth = []

    # Get reference statistics
    global_preg_rate = df["pregnant"].mean()
    global_cl_mean = df["cl_measure_mm"].mean()
    global_cl_std = df["cl_measure_mm"].std()

    techs = df["technician_name"].dropna().unique()
    if len(techs) == 0:
        techs = ["SyntheticTech"]

    base_date = pd.Timestamp("2025-11-01")

    for i in range(n_anomalous_batches):
        anomaly_type = ["low_preg_rate", "cl_drift", "grade_anomaly", "volume_spike", "mixed"][i % 5]
        tech = rng.choice(techs)
        batch_date = base_date + pd.Timedelta(days=30 * i)
        batch_period = batch_date.to_period("M")

        if anomaly_type == "low_preg_rate":
            # Technician with 0% pregnancy rate in a month
            n_records = 8
            rows = _generate_base_rows(n_records, tech, batch_date, rng, df)
            for r in rows:
                r["pregnant"] = 0.0  # all failures
            ground_truth.append({
                "batch_index": i,
                "type": "low_pregnancy_rate",
                "technician": tech,
                "period": str(batch_period),
                "expected_pregnancy_rate": 0.0,
                "severity": "critical",
                "description": f"Technician {tech} has 0% pregnancy rate in {batch_period}",
            })

        elif anomaly_type == "cl_drift":
            # CL measurements shifted way above normal (calibration issue)
            n_records = 6
            rows = _generate_base_rows(n_records, tech, batch_date, rng, df)
            for r in rows:
                r["cl_measure_mm"] = global_cl_mean + 3 * global_cl_std + rng.uniform(0, 5)
            ground_truth.append({
                "batch_index": i,
                "type": "cl_measurement_drift",
                "technician": tech,
                "period": str(batch_period),
                "expected_avg_cl": float(global_cl_mean + 3 * global_cl_std),
                "severity": "warning",
                "description": f"CL measurements abnormally high for {tech} in {batch_period}",
            })

        elif anomaly_type == "grade_anomaly":
            # All embryos graded as 4 (worst quality) — unusual
            n_records = 7
            rows = _generate_base_rows(n_records, tech, batch_date, rng, df)
            for r in rows:
                r["embryo_grade"] = 4.0
                r["pregnant"] = rng.choice([0.0, 0.0, 0.0, 1.0])  # ~25% rate
            ground_truth.append({
                "batch_index": i,
                "type": "grade_anomaly",
                "technician": tech,
                "period": str(batch_period),
                "expected_avg_grade": 4.0,
                "severity": "warning",
                "description": f"All embryos grade 4 for {tech} in {batch_period}",
            })

        elif anomaly_type == "volume_spike":
            # Way more transfers than normal in a single month
            n_records = 40
            rows = _generate_base_rows(n_records, tech, batch_date, rng, df)
            ground_truth.append({
                "batch_index": i,
                "type": "volume_spike",
                "technician": tech,
                "period": str(batch_period),
                "expected_transfer_count": n_records,
                "severity": "info",
                "description": f"Unusual volume ({n_records} transfers) for {tech} in {batch_period}",
            })

        elif anomaly_type == "mixed":
            # Low pregnancy + high CL + bad grades combined
            n_records = 10
            rows = _generate_base_rows(n_records, tech, batch_date, rng, df)
            for r in rows:
                r["pregnant"] = 0.0
                r["cl_measure_mm"] = global_cl_mean + 2.5 * global_cl_std
                r["embryo_grade"] = rng.choice([3.0, 4.0])
            ground_truth.append({
                "batch_index": i,
                "type": "mixed_anomaly",
                "technician": tech,
                "period": str(batch_period),
                "severity": "critical",
                "description": f"Multiple QC failures for {tech} in {batch_period}",
            })

        synthetic_rows.extend(rows)

    # Create synthetic DataFrame
    synth_df = pd.DataFrame(synthetic_rows)

    # Tag synthetic records
    df = df.copy()
    df["is_synthetic"] = False
    synth_df["is_synthetic"] = True

    # Combine
    augmented = pd.concat([df, synth_df], ignore_index=True)

    # Recompute year_month for new records
    augmented["year_month"] = augmented["et_date"].dt.to_period("M")

    logger.info(
        f"Injected {len(synthetic_rows)} synthetic records "
        f"({n_anomalous_batches} anomalous batches), "
        f"total: {len(augmented)} records"
    )

    return augmented, ground_truth


def _generate_base_rows(
    n: int,
    technician: str,
    base_date: pd.Timestamp,
    rng: np.random.RandomState,
    ref_df: pd.DataFrame,
) -> list[dict]:
    """Generate n plausible-looking ET rows for a given technician and month."""
    global_cl_mean = ref_df["cl_measure_mm"].mean()
    global_cl_std = max(ref_df["cl_measure_mm"].std(), 1.0)
    global_preg_rate = ref_df["pregnant"].mean()

    rows = []
    for j in range(n):
        rows.append({
            "et_date": base_date + pd.Timedelta(days=rng.randint(0, 28)),
            "technician_name": technician,
            "cl_measure_mm": max(5.0, rng.normal(global_cl_mean, global_cl_std)),
            "embryo_stage": rng.choice([5.0, 6.0, 7.0]),
            "embryo_grade": rng.choice([1.0, 1.0, 1.0, 2.0]),  # mostly grade 1
            "bc_score": rng.uniform(1.0, 5.0),
            "heat_day": rng.choice([6.0, 7.0, 8.0]),
            "pregnant": float(rng.random() < global_preg_rate),
            "protocol_name": "CIDR-7Day",
            "donor_breed": "Holstein",
            "fresh_or_frozen": rng.choice(["Fresh", "Frozen"]),
            "customer_id": "SYNTH",
            "cl_side": rng.choice(["Left", "Right"]),
            "semen_type": "Conventional",
        })
    return rows


def verify_detection(
    ground_truth: list[dict],
    detected_anomalies: pd.DataFrame,
) -> dict:
    """Verify that injected anomalies were detected.

    Parameters
    ----------
    ground_truth : List of injected anomaly descriptions
    detected_anomalies : DataFrame from Isolation Forest with is_anomaly column

    Returns
    -------
    dict with detection_rate, true_positives, false_negatives
    """
    # Matched on (technician, period), because that is the only identity the
    # injected rows and the detected batches share. The previous version asked
    # for an ``is_synthetic`` column on the batch frame; row-level aggregation
    # never produced one, so ``DataFrame.get`` returned the scalar False and
    # ``df[False]`` raised KeyError — this whole verification path had never run.
    if "is_anomaly" not in detected_anomalies.columns:
        raise ValueError("detected_anomalies has no is_anomaly column")

    flagged = {
        (str(row.get("technician_name")), str(row.get("period")))
        for _, row in detected_anomalies[detected_anomalies["is_anomaly"]].iterrows()
    }

    hits, misses = [], []
    for truth in ground_truth:
        key = (str(truth.get("technician")), str(truth.get("period")))
        (hits if key in flagged else misses).append(
            {
                "type": truth.get("type"),
                "technician": truth.get("technician"),
                "period": truth.get("period"),
            }
        )

    # Detection happens per batch, and several faults can land in one batch
    # (the CL drift and the grade anomaly both hit Masroor/2025-12). Scoring
    # per fault therefore caps recall below 1.0 by construction, so the rate is
    # reported over distinct affected batches and the per-fault counts stay
    # alongside it.
    injected_keys = {
        (str(t.get("technician")), str(t.get("period"))) for t in ground_truth
    }
    found_keys = injected_keys & flagged

    return {
        "detection_rate": round(len(found_keys) / max(len(injected_keys), 1), 4),
        "batches_injected": len(injected_keys),
        "batches_detected": len(found_keys),
        "true_positives": len(hits),
        "false_negatives": len(misses),
        "total_injected": len(ground_truth),
        "detected": hits,
        "missed": misses,
        "flagged_not_injected": len(flagged - injected_keys),
    }
