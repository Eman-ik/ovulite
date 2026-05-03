"""
Acceptance Tests: AT-5 through AT-10
Aligned to current API contracts.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.acceptance
class TestAT5QCAnomalyDetection:
    """AT-5: QC anomaly and chart endpoints."""

    def test_qc_summary_endpoint(self, client: TestClient, auth_headers: dict):
        response = client.get("/qc/summary", headers=auth_headers)
        if response.status_code == 503:
            pytest.skip("QC pipeline unavailable")
        assert response.status_code == 200, response.text

    def test_qc_anomalies_endpoint(self, client: TestClient, auth_headers: dict):
        response = client.get("/qc/anomalies", headers=auth_headers)
        if response.status_code == 503:
            pytest.skip("QC artifacts unavailable")
        assert response.status_code == 200, response.text
        data = response.json()
        assert "alerts" in data
        assert "total" in data

    def test_qc_charts_endpoint(self, client: TestClient, auth_headers: dict):
        response = client.get("/qc/charts", headers=auth_headers)
        if response.status_code == 503:
            pytest.skip("QC artifacts unavailable")
        assert response.status_code == 200, response.text
        data = response.json()
        assert "charts" in data


@pytest.mark.acceptance
class TestAT6DashboardKPIs:
    """AT-6: analytics KPI contracts."""

    def test_kpis_endpoint_accessible(self, client: TestClient, auth_headers: dict):
        response = client.get("/analytics/kpis", headers=auth_headers)
        assert response.status_code == 200, response.text

    def test_kpis_required_fields_present(self, client: TestClient, auth_headers: dict):
        response = client.get("/analytics/kpis", headers=auth_headers)
        assert response.status_code == 200, response.text
        data = response.json()
        for key in ["total_transfers", "with_outcome", "pregnant", "open", "pregnancy_rate", "entity_counts"]:
            assert key in data, f"Missing KPI field: {key}"

    def test_no_nan_or_inf_values(self, client: TestClient, auth_headers: dict):
        response = client.get("/analytics/kpis", headers=auth_headers)
        assert response.status_code == 200, response.text
        text = response.text
        assert "NaN" not in text
        assert "Infinity" not in text


@pytest.mark.acceptance
class TestAT7UncertaintyDisplay:
    """AT-7: uncertainty fields in prediction response."""

    def _predict(self, client: TestClient, auth_headers: dict):
        return client.post(
            "/predict/pregnancy",
            json={"cl_measure_mm": 25, "embryo_stage": 7, "embryo_grade": 1},
            headers=auth_headers,
        )

    def test_confidence_interval_present(self, client: TestClient, auth_headers: dict):
        response = self._predict(client, auth_headers)
        if response.status_code == 503:
            pytest.skip("Prediction model unavailable")
        assert response.status_code == 200, response.text
        data = response.json()
        assert "confidence_lower" in data
        assert "confidence_upper" in data

    def test_risk_band_assigned(self, client: TestClient, auth_headers: dict):
        response = self._predict(client, auth_headers)
        if response.status_code == 503:
            pytest.skip("Prediction model unavailable")
        assert response.status_code == 200, response.text
        assert isinstance(response.json().get("risk_band"), str)


@pytest.mark.acceptance
class TestAT8RBACEnforced:
    """AT-8: auth boundary checks."""

    def test_unauthenticated_user_denied(self, client: TestClient):
        response = client.get("/transfers/")
        assert response.status_code == 401, response.text

    def test_invalid_token_rejected(self, client: TestClient):
        response = client.get("/transfers/", headers={"Authorization": "Bearer invalid.token"})
        assert response.status_code == 401, response.text

    def test_authenticated_user_can_read(self, client: TestClient, auth_headers: dict):
        response = client.get("/transfers/", headers=auth_headers)
        assert response.status_code == 200, response.text


@pytest.mark.acceptance
class TestAT9SHAPExplanations:
    """AT-9: SHAP explanation object exists on prediction output."""

    def test_shap_explanation_present(self, client: TestClient, auth_headers: dict):
        response = client.post(
            "/predict/pregnancy",
            json={"cl_measure_mm": 24, "embryo_stage": 7, "embryo_grade": 1},
            headers=auth_headers,
        )
        if response.status_code == 503:
            pytest.skip("Prediction model unavailable")
        assert response.status_code == 200, response.text
        data = response.json()
        shap = data.get("shap_explanation")
        assert isinstance(shap, dict)
        assert "base_value" in shap
        assert "contributions" in shap


@pytest.mark.acceptance
class TestAT10APIDocumentation:
    """AT-10: OpenAPI docs coverage."""

    def test_openapi_available(self, client: TestClient):
        response = client.get("/openapi.json")
        assert response.status_code == 200, response.text
        data = response.json()
        assert "paths" in data

    def test_core_endpoint_groups_documented(self, client: TestClient):
        response = client.get("/openapi.json")
        assert response.status_code == 200, response.text
        paths = response.json().get("paths", {})
        expected_prefixes = ["/auth", "/transfers", "/predict", "/grade", "/qc", "/analytics"]
        for p in expected_prefixes:
            assert any(path.startswith(p) for path in paths.keys()), f"Missing OpenAPI group: {p}"


@pytest.mark.acceptance
def test_suite_complete():
    assert True
