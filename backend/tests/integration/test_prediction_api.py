"""Integration tests for prediction endpoints."""

import pytest


@pytest.mark.integration
def test_predict_pregnancy_contract(client, auth_headers, sample_prediction_input):
    """Prediction endpoint should return full contract or clear artifact error."""
    response = client.post(
        "/predict/pregnancy",
        json=sample_prediction_input,
        headers=auth_headers,
    )

    assert response.status_code in (200, 503), response.text

    if response.status_code == 503:
        assert "trained model" in response.text.lower() or "artifact" in response.text.lower()
        return

    data = response.json()
    assert 0.0 <= data["probability"] <= 1.0
    assert 0.0 <= data["confidence_lower"] <= 1.0
    assert 0.0 <= data["confidence_upper"] <= 1.0
    assert data["confidence_lower"] <= data["confidence_upper"]
    assert data["risk_band"] in ["Low", "Medium", "High"]
    assert "model_name" in data and data["model_name"]
    assert "model_version" in data and data["model_version"]
    assert "shap_explanation" in data
    assert "base_value" in data["shap_explanation"]
    assert isinstance(data["shap_explanation"]["contributions"], list)


@pytest.mark.integration
def test_predict_pregnancy_validation_errors(client, auth_headers):
    invalid_input = {
        "cl_measure_mm": -5,
        "embryo_stage": 99,
    }
    response = client.post(
        "/predict/pregnancy",
        json=invalid_input,
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.integration
def test_model_info_endpoint_contract(client, auth_headers):
    response = client.get("/predict/model-info", headers=auth_headers)
    assert response.status_code in (200, 503), response.text
    if response.status_code == 200:
        data = response.json()
        assert "model_name" in data
        assert "model_version" in data
        assert "n_features" in data
