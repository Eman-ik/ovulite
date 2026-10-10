"""The contract POST /predict/pregnancy must hold regardless of model quality.

The deployed artifact does not discriminate (ROC-AUC 0.510, permutation
p = 0.143/0.190), so none of these assert that a prediction is *good*. They
assert it is *well-formed, scoped, persisted and honest* — the properties that
stay required when the model is eventually replaced by one that works.

Deliberately not asserted: that probabilities vary between cases. They barely
do (0.112-0.238 across 225 real predictions), and pinning that would encode the
current model's weakness as a requirement.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

VALID_INPUT = {
    "cl_measure_mm": 18.0,
    "embryo_stage": 7,
    "embryo_grade": 1,
    "bc_score": 3.0,
    "cl_side": "Left",
    "protocol_name": "CIDR+GnRH+PGF+GnRH",
    "fresh_or_frozen": "Fresh",
    "semen_type": "Conventional",
    "donor_breed": "Grey Brahman",
}

BANDS = {"Low", "Moderate", "High"}


def _predict(client, headers, **overrides):
    payload = {**VALID_INPUT, **overrides}
    return client.post("/predict/pregnancy", json=payload, headers=headers)


@pytest.fixture
def prediction(client: TestClient, auth_headers):
    response = _predict(client, auth_headers)
    if response.status_code == 503:
        pytest.skip("no trained artifact available in this environment")
    assert response.status_code == 200, response.text
    return response.json()


# ── Output shape ──────────────────────────────────────────────────────────

class TestPredictionOutput:
    def test_probability_is_a_proportion(self, prediction):
        assert 0.0 <= prediction["probability"] <= 1.0

    def test_percent_agrees_with_probability(self, prediction):
        assert prediction["probability_percent"] == pytest.approx(
            prediction["probability"] * 100, abs=0.05
        )

    def test_interval_brackets_the_estimate(self, prediction):
        lower, upper = prediction["confidence_lower"], prediction["confidence_upper"]
        assert 0.0 <= lower <= prediction["probability"] <= upper <= 1.0

    def test_band_is_one_of_the_three(self, prediction):
        assert prediction["risk_band"] in BANDS

    def test_band_matches_the_probability_it_reports(self, prediction):
        """The band must be derivable from the number shown beside it."""
        from ml.config import get_risk_band

        assert prediction["risk_band"] == get_risk_band(prediction["probability"])

    def test_carries_its_own_provenance(self, prediction):
        for field in ("model_name", "model_version", "feature_schema_version", "request_id"):
            assert prediction[field], f"{field} is empty"

    def test_explanation_is_labelled_as_a_surrogate(self, prediction):
        """The live path uses a linear surrogate, not Shapley values.

        Calling it SHAP in the payload would misrepresent it; the UI reads this
        field to say so.
        """
        shap = prediction["shap_explanation"]
        assert shap["contributions"], "no contributions returned"
        assert "surrogate" in shap["method"] or shap.get("is_true_shap") is False

    def test_uncertainty_is_reported(self, prediction):
        assert prediction["uncertainty_level"] in {"Low", "Moderate", "High"}


# ── Band boundaries at the API level ──────────────────────────────────────

class TestBandBoundaries:
    @pytest.mark.parametrize(
        "probability,expected",
        [(0.0, "Low"), (0.3499, "Low"), (0.35, "Moderate"),
         (0.6499, "Moderate"), (0.65, "High"), (1.0, "High")],
    )
    def test_boundaries(self, probability, expected):
        from ml.config import get_risk_band

        assert get_risk_band(probability) == expected


# ── Input validation ──────────────────────────────────────────────────────

class TestInputValidation:
    def test_missing_required_feature_is_refused(self, client: TestClient, auth_headers):
        payload = {k: v for k, v in VALID_INPUT.items() if k != "cl_measure_mm"}
        assert client.post("/predict/pregnancy", json=payload, headers=auth_headers).status_code == 422

    def test_optional_features_may_be_absent(self, client: TestClient, auth_headers):
        """cl_measure_mm and embryo_stage are required; the rest are not."""
        response = client.post(
            "/predict/pregnancy",
            json={"cl_measure_mm": 18.0, "embryo_stage": 7},
            headers=auth_headers,
        )
        if response.status_code == 503:
            pytest.skip("no trained artifact available")
        assert response.status_code == 200, response.text

    @pytest.mark.parametrize(
        "field,value",
        [
            ("cl_measure_mm", -1),       # below ge=0
            ("cl_measure_mm", 51),       # above le=50
            ("embryo_stage", 0),         # below ge=1
            ("embryo_stage", 10),        # above le=9
            ("embryo_grade", 5),         # above le=4
            ("cl_measure_mm", "wide"),   # wrong type
        ],
    )
    def test_out_of_range_values_are_refused(self, client, auth_headers, field, value):
        assert _predict(client, auth_headers, **{field: value}).status_code == 422

    def test_unseen_category_is_flagged_not_rejected(self, client: TestClient, auth_headers):
        """An unknown protocol is out-of-distribution, not invalid.

        Refusing it would hide the case; the model answers and marks itself
        unreliable instead.
        """
        response = _predict(client, auth_headers, protocol_name="Protocol That Does Not Exist")
        if response.status_code == 503:
            pytest.skip("no trained artifact available")
        assert response.status_code == 200
        body = response.json()
        assert body["is_ood"] is True
        assert body["ood_reasons"], "flagged OOD but gave no reason"


# ── Authorization and tenancy ─────────────────────────────────────────────

class TestAccessControl:
    def test_anonymous_is_refused(self, client: TestClient):
        assert client.post("/predict/pregnancy", json=VALID_INPUT).status_code == 401

    def test_history_requires_auth(self, client: TestClient):
        assert client.get("/predict/history").status_code == 401

    def test_history_excludes_other_tenants(
        self, client: TestClient, auth_headers, db_session, admin_org_id
    ):
        """A prediction belonging to another organization must not appear.

        OrganizationScopedMixin does no automatic filtering, so every endpoint
        has to scope its own query. This is the test that catches a forgotten one.
        """
        from app.models.prediction import Prediction

        db_session.add(
            Prediction(
                model_name="other_tenant", model_version="v1",
                probability=Decimal("0.90"), risk_band="High",
                organization_id=admin_org_id + 1,
            )
        )
        db_session.commit()

        body = client.get("/predict/history", headers=auth_headers).json()
        assert all(p["model_name"] != "other_tenant" for p in body["predictions"])


# ── Persistence, history, outcome ─────────────────────────────────────────

class TestLifecycle:
    def test_prediction_is_persisted_and_retrievable(
        self, client: TestClient, auth_headers, prediction
    ):
        body = client.get("/predict/history", headers=auth_headers).json()
        assert body["total"] >= 1
        assert any(p["prediction_id"] == prediction["prediction_id"] for p in body["predictions"])

    def test_recorded_outcome_appears_in_history(
        self, client: TestClient, auth_headers, prediction
    ):
        pid = prediction["prediction_id"]
        response = client.patch(
            f"/predict/{pid}/outcome", json={"actual_outcome": "Pregnant"}, headers=auth_headers
        )
        assert response.status_code == 200, response.text

        body = client.get("/predict/history", headers=auth_headers).json()
        stored = next(p for p in body["predictions"] if p["prediction_id"] == pid)
        assert stored["actual_outcome"] == "Pregnant"

    def test_outcome_does_not_alter_the_prediction(
        self, client: TestClient, auth_headers, prediction
    ):
        """Recording what happened must never edit what was predicted.

        If the stored probability or band could move after the fact, every
        retrospective evaluation of this model would be contaminated.
        """
        pid = prediction["prediction_id"]
        before = next(
            p for p in client.get("/predict/history", headers=auth_headers).json()["predictions"]
            if p["prediction_id"] == pid
        )
        client.patch(
            f"/predict/{pid}/outcome", json={"actual_outcome": "Open"}, headers=auth_headers
        )
        after = next(
            p for p in client.get("/predict/history", headers=auth_headers).json()["predictions"]
            if p["prediction_id"] == pid
        )
        for field in ("probability", "risk_band", "model_version", "predicted_at"):
            assert before[field] == after[field], f"{field} changed after recording an outcome"

    def test_outcome_on_another_tenants_prediction_is_refused(
        self, client: TestClient, auth_headers, db_session, admin_org_id
    ):
        from app.models.prediction import Prediction

        foreign = Prediction(
            model_name="other_tenant", model_version="v1",
            probability=Decimal("0.5"), risk_band="Moderate",
            organization_id=admin_org_id + 1,
        )
        db_session.add(foreign)
        db_session.commit()
        db_session.refresh(foreign)

        response = client.patch(
            f"/predict/{foreign.prediction_id}/outcome",
            json={"actual_outcome": "Pregnant"},
            headers=auth_headers,
        )
        assert response.status_code == 404
