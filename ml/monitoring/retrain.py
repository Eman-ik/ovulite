"""Retrain-job decision logic (Module 7).

This is deliberately NOT full AutoML. It writes a reproducible audit-trail
record (a `retrain_jobs` row) whenever drift is detected, and leaves the
actual retrain script (ml/train_pipeline.py) to be run manually or via the
n8n HTTP Request node -> POST /monitoring/retrain-jobs/{id}/run.
"""

from datetime import datetime, timezone


def build_retrain_job_record(
    perf_drift: bool,
    perf_details: dict,
    pop_drift: bool,
    pop_details: dict,
    model_version: str,
    triggered_by: str = "AUTO",
) -> dict | None:
    """Return a dict ready to insert as a RetrainJob row, or None if no
    retrain is warranted.
    """
    if not (perf_drift or pop_drift):
        return None

    reasons = []
    if perf_drift:
        reasons.append("performance_drift")
    if pop_drift:
        reasons.append("population_drift")

    reason_text = (
        f"Drift detected ({', '.join(reasons)}) for model_version={model_version}. "
        f"performance_details={perf_details}; population_details={pop_details}"
    )

    return {
        "reason": reason_text,
        "status": "PENDING",
        "triggered_by": triggered_by,
        "drift_details": {
            "performance": perf_details,
            "population": pop_details,
            "flags": reasons,
        },
        "model_version": model_version,
        "artifact_path": None,
        "triggered_at": datetime.now(timezone.utc),
    }
