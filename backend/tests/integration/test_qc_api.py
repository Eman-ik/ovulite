"""Integration tests for QC API endpoints and artifact persistence."""

from __future__ import annotations

from pathlib import Path

import pytest


QC_ARTIFACTS_DIR = Path(__file__).resolve().parents[3] / "ml" / "artifacts" / "qc"


@pytest.mark.integration
def test_qc_run_triggers_pipeline_and_persists_artifacts(client, auth_headers):
    response = client.post("/qc/run", headers=auth_headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body.get("status") == "complete"
    assert "summary" in body
    assert "alert_count" in body

    # Core persisted artifacts used by API endpoints
    expected_files = [
        "qc_summary.json",
        "qc_alerts.json",
        "qc_charts.json",
        "isolation_forest.joblib",
        "iforest_meta.json",
        # Added for retrievability/auditability
        "qc_technicians.json",
        "qc_protocols.json",
        "qc_monthly_metrics.json",
        "qc_anomalous_batches.json",
    ]
    for name in expected_files:
        assert (QC_ARTIFACTS_DIR / name).exists(), f"Missing artifact {name}"


@pytest.mark.integration
def test_qc_summary_contract(client, auth_headers):
    response = client.get("/qc/summary", headers=auth_headers)
    assert response.status_code == 200, response.text

    body = response.json()
    required = [
        "total_records",
        "total_batches",
        "anomalous_batches",
        "anomaly_rate",
        "chart_alerts",
        "total_alerts",
        "technicians_analyzed",
        "protocols_analyzed",
        "months_analyzed",
    ]
    for key in required:
        assert key in body


@pytest.mark.integration
def test_qc_anomalies_contract_and_filtering(client, auth_headers):
    response = client.get("/qc/anomalies", headers=auth_headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert "alerts" in body and isinstance(body["alerts"], list)
    assert "total" in body
    assert "critical_count" in body
    assert "warning_count" in body
    assert "info_count" in body

    if body["alerts"]:
        a = body["alerts"][0]
        # Frontend-required shape
        for key in [
            "alert_type",
            "entity_type",
            "entity_id",
            "severity",
            "metric",
            "description",
        ]:
            assert key in a

    # Severity filter behavior
    filtered = client.get("/qc/anomalies?severity=critical&limit=5", headers=auth_headers)
    assert filtered.status_code == 200, filtered.text
    f_body = filtered.json()
    assert len(f_body["alerts"]) <= 5
    for a in f_body["alerts"]:
        assert a["severity"] == "critical"


@pytest.mark.integration
def test_qc_charts_contract_matches_frontend_expectations(client, auth_headers):
    response = client.get("/qc/charts", headers=auth_headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert "charts" in body and isinstance(body["charts"], list)
    assert "metrics" in body and isinstance(body["metrics"], list)

    if body["charts"]:
        chart = body["charts"][0]
        for key in ["metric", "periods", "ewma", "cusum", "alerts"]:
            assert key in chart

        if chart["ewma"]:
            p = chart["ewma"][0]
            for key in ["value", "ewma", "target", "ucl", "lcl", "out_of_control"]:
                assert key in p

        if chart["cusum"]:
            p = chart["cusum"][0]
            for key in [
                "value",
                "cusum_pos",
                "cusum_neg",
                "threshold_pos",
                "threshold_neg",
                "shift_detected",
                "shift_direction",
            ]:
                assert key in p


@pytest.mark.integration
def test_qc_technicians_retrievable_contract(client, auth_headers):
    response = client.get("/qc/technicians", headers=auth_headers)
    assert response.status_code == 200, response.text

    body = response.json()
    assert "technicians" in body and isinstance(body["technicians"], list)
    assert "total" in body
    assert "global_pregnancy_rate" in body

    if body["technicians"]:
        t = body["technicians"][0]
        for key in [
            "technician_name",
            "transfer_count",
            "pregnancy_rate",
            "avg_cl_measure",
            "std_cl_measure",
            "avg_embryo_grade",
            "avg_bc_score",
            "preg_rate_vs_mean",
        ]:
            assert key in t


@pytest.mark.integration
@pytest.mark.parametrize(
    "endpoint,method",
    [
        ("/qc/summary", "get"),
        ("/qc/anomalies", "get"),
        ("/qc/charts", "get"),
        ("/qc/technicians", "get"),
        ("/qc/run", "post"),
    ],
)
def test_qc_endpoints_require_auth(client, endpoint, method):
    response = getattr(client, method)(endpoint)
    assert response.status_code == 401, f"Expected 401 for {method.upper()} {endpoint}"
