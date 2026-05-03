"""QC pipeline runner — ties all QC modules together.

Usage:
    python -m ml.qc.run_pipeline                    # Full pipeline
    python -m ml.qc.run_pipeline --with-synthetic   # Include synthetic anomalies
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Ensure project root on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run_qc_pipeline(
    csv_path: Path | None = None,
    with_synthetic: bool = False,
    save_dir: Path | None = None,
) -> dict:
    """Run full QC pipeline: features → anomaly detection → control charts → alerts.

    Returns
    -------
    dict with keys: technician_stats, anomalies, charts, alerts, summary
    """
    from ml.qc.alerts import combine_and_prioritize, generate_chart_alerts, generate_iforest_alerts
    from ml.qc.anomaly_detector import train_isolation_forest
    from ml.qc.config import ARTIFACTS_DIR
    from ml.qc.control_charts import build_control_charts
    from ml.qc.features import (
        build_qc_feature_matrix,
        compute_monthly_metrics,
        compute_protocol_stats,
        compute_technician_stats,
        load_et_data,
    )

    if save_dir is None:
        save_dir = ARTIFACTS_DIR

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("QC Pipeline: Loading data")
    logger.info("=" * 60)

    df = load_et_data(csv_path)
    logger.info(f"Loaded {len(df)} ET records")

    # Inject synthetic anomalies if requested
    ground_truth = None
    if with_synthetic:
        from ml.qc.synthetic import inject_synthetic_anomalies
        df, ground_truth = inject_synthetic_anomalies(df)
        logger.info(f"Injected synthetic anomalies, total records: {len(df)}")

    # ── Feature engineering ──
    logger.info("Computing QC features...")
    tech_stats = compute_technician_stats(df)
    protocol_stats = compute_protocol_stats(df)
    monthly = compute_monthly_metrics(df)
    X, batch_df = build_qc_feature_matrix(df)
    logger.info(f"Feature matrix: {X.shape[0]} batches × {X.shape[1]} features")

    # ── Isolation Forest ──
    logger.info("Training Isolation Forest...")
    model, results_df = train_isolation_forest(X, batch_df, save_dir=save_dir)
    n_anomalies = results_df["is_anomaly"].sum()
    logger.info(f"Detected {n_anomalies} anomalous batches")

    # ── Control Charts ──
    logger.info("Building control charts...")
    charts = build_control_charts(monthly)
    n_chart_alerts = sum(len(c["alerts"]) for c in charts.values())
    logger.info(f"Control chart alerts: {n_chart_alerts}")

    # ── Alerts ──
    logger.info("Generating alerts...")
    iforest_alerts = generate_iforest_alerts(results_df)
    chart_alerts = generate_chart_alerts(charts)
    all_alerts = combine_and_prioritize(iforest_alerts, chart_alerts)
    logger.info(f"Total alerts: {len(all_alerts)}")

    # ── Verification (if synthetic) ──
    detection_result = None
    if with_synthetic and ground_truth:
        from ml.qc.synthetic import verify_detection
        detection_result = verify_detection(ground_truth, results_df)
        logger.info(f"Detection rate: {detection_result['detection_rate']:.0%}")

    # ── Save results ──
    save_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "total_records": len(df),
        "total_batches": len(batch_df),
        "anomalous_batches": int(n_anomalies),
        "anomaly_rate": round(float(n_anomalies / max(len(batch_df), 1)), 4),
        "chart_alerts": n_chart_alerts,
        "total_alerts": len(all_alerts),
        "technicians_analyzed": len(tech_stats),
        "protocols_analyzed": len(protocol_stats),
        "months_analyzed": len(monthly),
        "global_pregnancy_rate": round(float(df["pregnant"].mean()), 4)
        if "pregnant" in df.columns and len(df) > 0
        else None,
    }

    if detection_result:
        summary["synthetic_detection"] = detection_result

    with open(save_dir / "qc_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # Serialize charts for API (convert DataFrames to lists)
    charts_serializable = {}
    for metric, data in charts.items():
        charts_serializable[metric] = {
            "ewma": data["ewma"].to_dict(orient="records") if not data["ewma"].empty else [],
            "cusum": data["cusum"].to_dict(orient="records") if not data["cusum"].empty else [],
            "alerts": data["alerts"],
            "periods": data["periods"],
        }

    with open(save_dir / "qc_charts.json", "w") as f:
        json.dump(charts_serializable, f, indent=2, default=str)

    with open(save_dir / "qc_alerts.json", "w") as f:
        json.dump(all_alerts, f, indent=2)

    # Persist additional QC artifacts for API retrieval and auditability.
    with open(save_dir / "qc_technicians.json", "w") as f:
        json.dump(tech_stats.to_dict(orient="records"), f, indent=2, default=str)

    with open(save_dir / "qc_protocols.json", "w") as f:
        json.dump(protocol_stats.to_dict(orient="records"), f, indent=2, default=str)

    with open(save_dir / "qc_monthly_metrics.json", "w") as f:
        json.dump(monthly.to_dict(orient="records"), f, indent=2, default=str)

    with open(save_dir / "qc_anomalous_batches.json", "w") as f:
        json.dump(
            results_df[results_df["is_anomaly"]].to_dict(orient="records"),
            f,
            indent=2,
            default=str,
        )

    logger.info("=" * 60)
    logger.info(f"QC Pipeline complete. Artifacts saved to {save_dir}")
    logger.info(f"Summary: {json.dumps(summary, indent=2)}")
    logger.info("=" * 60)

    return {
        "technician_stats": tech_stats,
        "protocol_stats": protocol_stats,
        "monthly_metrics": monthly,
        "anomalies": results_df,
        "charts": charts_serializable,
        "alerts": all_alerts,
        "summary": summary,
    }


def main():
    parser = argparse.ArgumentParser(description="Run QC anomaly detection pipeline")
    parser.add_argument("--csv", type=str, default=None, help="Path to ET Data CSV")
    parser.add_argument("--with-synthetic", action="store_true", help="Inject synthetic anomalies for testing")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )

    csv_path = Path(args.csv) if args.csv else None
    run_qc_pipeline(csv_path=csv_path, with_synthetic=args.with_synthetic)


if __name__ == "__main__":
    main()
