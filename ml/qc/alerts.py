"""Alert system for QC anomalies (ROADMAP task 4.7).

Provides severity-tagged anomaly alerts from both Isolation Forest
and control chart violations.
"""

import logging
from datetime import datetime, timezone

import pandas as pd

logger = logging.getLogger(__name__)


class Alert:
    """Structured QC alert."""

    def __init__(
        self,
        alert_type: str,
        entity_type: str,
        entity_id: str,
        severity: str,
        metric: str,
        metric_value: float,
        baseline_value: float | None = None,
        description: str = "",
        period: str | None = None,
    ):
        self.alert_type = alert_type
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.severity = severity
        self.metric = metric
        self.metric_value = metric_value
        self.baseline_value = baseline_value
        self.description = description
        self.period = period
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "alert_type": self.alert_type,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "severity": self.severity,
            "metric": self.metric,
            "metric_value": round(self.metric_value, 4) if self.metric_value is not None else None,
            "baseline_value": round(self.baseline_value, 4) if self.baseline_value is not None else None,
            "description": self.description,
            "period": self.period,
            "timestamp": self.timestamp,
        }


def generate_iforest_alerts(
    results_df: pd.DataFrame,
    global_stats: dict | None = None,
) -> list[dict]:
    """Generate alerts from Isolation Forest anomaly detection results.

    Parameters
    ----------
    results_df : Output from anomaly_detector.train_isolation_forest()
    global_stats : Optional dict with global baseline stats

    Returns
    -------
    List of alert dicts
    """
    anomalies = results_df[results_df["is_anomaly"]].copy()
    alerts = []

    # The cohort these batches were z-scored against. This is the baseline an
    # alert has to quote: "26% against a cohort 35%" is actionable, a bare
    # anomaly score is not.
    cohort = {
        col: float(results_df[col].mean())
        for col in ("pregnancy_rate", "avg_cl_measure", "avg_embryo_grade")
        if col in results_df.columns and results_df[col].notna().any()
    }

    for _, row in anomalies.iterrows():
        tech = row.get("technician_name", "Unknown")
        period = row.get("period", "Unknown")
        severity = row.get("anomaly_severity", "warning")
        score = row.get("anomaly_score", 0)

        # Determine what's anomalous, and which metric moved furthest — that is
        # the one the alert names, so it can be quoted against its baseline.
        descriptions = []
        driver = None  # (abs_z, column, value)

        for col, label, fmt in (
            ("pregnancy_rate", "pregnancy rate", lambda v: f"{v:.0%}"),
            ("avg_cl_measure", "CL measure", lambda v: f"{v:.1f}mm"),
            ("avg_embryo_grade", "embryo grade avg", lambda v: f"{v:.1f}"),
        ):
            if col not in row or pd.isna(row[col]):
                continue
            z = row.get(f"z_{col}", 0)
            if pd.isna(z) or abs(z) <= 1.5:
                continue
            direction = "low" if z < 0 else "high"
            descriptions.append(f"{label} {fmt(row[col])} ({direction})")
            if driver is None or abs(z) > driver[0]:
                driver = (abs(z), col, float(row[col]))

        if driver is not None:
            metric, metric_value = driver[1], driver[2]
            baseline = cohort.get(metric)
            desc = f"Anomalous batch: {', '.join(descriptions)}"
        else:
            # Flagged on the multivariate combination, with no single metric
            # past threshold. Naming one would invent a cause that isn't there.
            metric, metric_value = "composite_anomaly_score", float(score)
            baseline = (
                float(results_df["anomaly_score"].median())
                if "anomaly_score" in results_df.columns
                else None
            )
            desc = (
                f"Statistical anomaly detected (score: {score:.3f}); no single "
                "metric past threshold, flagged on the combination"
            )

        alert = Alert(
            alert_type="isolation_forest",
            entity_type="technician_batch",
            entity_id=f"{tech}/{period}",
            severity=severity,
            metric=metric,
            metric_value=metric_value,
            baseline_value=baseline,
            description=desc,
            period=period,
        )
        alerts.append(alert.to_dict())

    return alerts


def generate_chart_alerts(charts: dict) -> list[dict]:
    """Generate alerts from EWMA/CUSUM control chart violations.

    Parameters
    ----------
    charts : Output from control_charts.build_control_charts()

    Returns
    -------
    List of alert dicts
    """
    alerts = []

    for metric, data in charts.items():
        for chart_alert in data.get("alerts", []):
            alert = Alert(
                alert_type=chart_alert["type"],
                entity_type="system_metric",
                entity_id=metric,
                severity=chart_alert.get("severity", "warning"),
                metric=metric,
                metric_value=chart_alert.get("value", 0),
                baseline_value=chart_alert.get("baseline"),
                description=_format_chart_alert(chart_alert),
                period=chart_alert.get("period"),
            )
            alerts.append(alert.to_dict())

    return alerts


def _format_chart_alert(alert: dict) -> str:
    """Format a control chart alert into human-readable description."""
    metric = alert.get("metric", "metric")
    period = alert.get("period", "?")
    value = alert.get("value", 0)

    if alert["type"] == "ewma_violation":
        direction = alert.get("direction", "")
        return f"EWMA violation: {metric} = {value:.4f} ({direction}) in {period}"
    elif alert["type"] == "cusum_shift":
        direction = alert.get("shift_direction", "")
        return f"CUSUM shift detected: {metric} shifted {direction} in {period}"
    else:
        return f"Control chart alert: {metric} = {value:.4f} in {period}"


def combine_and_prioritize(
    iforest_alerts: list[dict],
    chart_alerts: list[dict],
) -> list[dict]:
    """Combine alerts from all sources and sort by severity.

    Priority: critical > warning > info
    Within same severity: sort by absolute metric value (most extreme first)
    """
    all_alerts = iforest_alerts + chart_alerts

    severity_order = {"critical": 0, "warning": 1, "info": 2}

    all_alerts.sort(
        key=lambda a: (
            severity_order.get(a.get("severity", "info"), 3),
            -abs(a.get("metric_value", 0)),
        )
    )

    return all_alerts
