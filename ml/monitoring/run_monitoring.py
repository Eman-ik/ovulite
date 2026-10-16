"""Outcome Tracking & Continuous Learning pipeline runner (Module 7).

Usage:
    python -m ml.monitoring.run_monitoring                  # real DB data (via backend)
    python -m ml.monitoring.run_monitoring --synthetic       # demo with synthetic data
    python -m ml.monitoring.run_monitoring --synthetic --inject-drift
"""

import argparse
import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)


def run_monitoring_pipeline(
    df_current,
    df_baseline,
    historical_metrics: list[dict] | None = None,
    model_version: str = "unknown",
    save_dir: Path | None = None,
    save_artifact: bool = True,
) -> dict:
    """Run the full Module 7 pipeline over two already-loaded DataFrames.

    Parameters
    ----------
    df_current : DataFrame with [probability, actual_outcome, cl_measure_mm, heat_day]
        Recent window (e.g. last 30 days) of resolved predictions.
    df_baseline : DataFrame, same columns
        Historical window used as the population-drift reference.
    historical_metrics : list of prior compute_rolling_metrics() outputs, used
        as the performance-drift baseline. If None, computed from df_baseline itself.
    model_version : the model version string these predictions came from.
    """
    from ml.monitoring.config import ARTIFACTS_DIR
    from ml.monitoring.drift import detect_performance_drift, detect_population_drift
    from ml.monitoring.metrics import compute_rolling_metrics
    from ml.monitoring.retrain import build_retrain_job_record

    if save_dir is None:
        save_dir = ARTIFACTS_DIR

    logger.info("Module 7: computing current-window metrics (n=%d)", len(df_current))
    current_metrics = compute_rolling_metrics(df_current)

    if historical_metrics is None:
        baseline_metrics = compute_rolling_metrics(df_baseline)
        historical_metrics = [baseline_metrics] * 3 if baseline_metrics["status"] == "ok" else []

    logger.info("Module 7: checking performance drift")
    perf_drift, perf_details = detect_performance_drift(current_metrics, historical_metrics)

    logger.info("Module 7: checking population drift")
    pop_drift, pop_details = detect_population_drift(df_current, df_baseline)

    drift_detected = perf_drift or pop_drift

    retrain_job = build_retrain_job_record(
        perf_drift, perf_details, pop_drift, pop_details, model_version
    )

    summary = {
        "model_version": model_version,
        "current_metrics": current_metrics,
        "performance_drift_detected": perf_drift,
        "performance_drift_details": perf_details,
        "population_drift_detected": pop_drift,
        "population_drift_details": pop_details,
        "drift_detected": drift_detected,
        "retrain_recommended": retrain_job is not None,
        "retrain_job": retrain_job,
    }

    # Read-only callers (GET /monitoring/drift) pass save_artifact=False so
    # that looking at the report never writes anything.
    if save_artifact:
        save_dir.mkdir(parents=True, exist_ok=True)
        with open(save_dir / "monitoring_summary.json", "w") as f:
            json.dump(summary, f, indent=2, default=str)

    logger.info("Module 7 complete. drift_detected=%s retrain_recommended=%s",
                drift_detected, retrain_job is not None)

    return summary


def main():
    parser = argparse.ArgumentParser(description="Run outcome-tracking / drift pipeline")
    parser.add_argument("--synthetic", action="store_true", help="Use synthetic predictions instead of real DB data")
    parser.add_argument("--inject-drift", action="store_true", help="Shift the synthetic current window to trigger drift")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s")

    if args.synthetic:
        from ml.monitoring.synthetic import generate_synthetic_predictions
        df_baseline, df_current = generate_synthetic_predictions(inject_drift=args.inject_drift)
        result = run_monitoring_pipeline(df_current, df_baseline, model_version="synthetic_demo")
    else:
        raise SystemExit(
            "Real-DB mode must be invoked from the backend (app.api.monitoring), "
            "which has the DB session. Use --synthetic for a standalone CLI run."
        )

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
