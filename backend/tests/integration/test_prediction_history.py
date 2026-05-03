"""Integration tests for prediction history endpoint."""

import pytest
from fastapi.testclient import TestClient


class TestPredictionHistory:
    """Test suite for GET /predict/history endpoint."""

    def test_prediction_history_requires_auth(self, client: TestClient):
        """Verify history endpoint requires authentication."""
        response = client.get("/predict/history")
        assert response.status_code == 401

    def test_prediction_history_returns_empty_list_initially(
        self, client: TestClient, auth_headers
    ):
        """Verify history returns empty list when no predictions exist."""
        response = client.get("/predict/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "predictions" in data
        assert "total" in data
        assert data["total"] == 0
        assert data["predictions"] == []

    def test_prediction_history_includes_recent_predictions(
        self, client: TestClient, auth_headers, db_session
    ):
        """Verify history returns predictions after they are created."""
        from app.models.prediction import Prediction
        from decimal import Decimal
        
        # Create test predictions
        pred1 = Prediction(
            model_name="test_model",
            model_version="v1.0",
            probability=Decimal("0.75"),
            confidence_lower=Decimal("0.65"),
            confidence_upper=Decimal("0.85"),
            risk_band="Medium",
            shap_json={"base_value": 0.5, "contributions": []},
        )
        pred2 = Prediction(
            model_name="test_model",
            model_version="v1.0",
            probability=Decimal("0.25"),
            confidence_lower=Decimal("0.15"),
            confidence_upper=Decimal("0.35"),
            risk_band="Low",
            shap_json={"base_value": 0.3, "contributions": []},
        )
        db_session.add(pred1)
        db_session.add(pred2)
        db_session.commit()
        
        # Fetch history
        response = client.get("/predict/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2
        assert len(data["predictions"]) >= 2
        
        # Verify structure
        first_pred = data["predictions"][0]
        assert "prediction_id" in first_pred
        assert "model_name" in first_pred
        assert "probability" in first_pred
        assert "risk_band" in first_pred
        assert "predicted_at" in first_pred
        assert "shap_json" in first_pred

    def test_prediction_history_filters_by_transfer_id(
        self, client: TestClient, auth_headers, db_session
    ):
        """Verify history can be filtered by transfer_id."""
        from app.models.prediction import Prediction
        from app.models.et_transfer import ETTransfer
        from decimal import Decimal
        from datetime import date
        
        # Create ET transfers first (foreign key requirement)
        transfer1 = ETTransfer(transfer_id=100, et_date=date(2024, 1, 1))
        transfer2 = ETTransfer(transfer_id=200, et_date=date(2024, 1, 2))
        db_session.add(transfer1)
        db_session.add(transfer2)
        db_session.commit()
       
        # Create predictions with different transfer IDs
        pred1 = Prediction(
            transfer_id=100,
            model_name="test_model",
            model_version="v1.0",
            probability=Decimal("0.75"),
            risk_band="Medium",
            shap_json={},
        )
        pred2 = Prediction(
            transfer_id=200,
            model_name="test_model",
            model_version="v1.0",
            probability=Decimal("0.25"),
            risk_band="Low",
            shap_json={},
        )
        db_session.add(pred1)
        db_session.add(pred2)
        db_session.commit()
        
        # Fetch history for transfer_id=100
        response = client.get(
            "/predict/history",
            params={"transfer_id": 100},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # Should only return predictions for transfer_id=100
        for pred in data["predictions"]:
            if pred["transfer_id"] is not None:
                assert pred["transfer_id"] == 100

    def test_prediction_history_respects_limit_parameter(
        self, client: TestClient, auth_headers, db_session
    ):
        """Verify history respects limit parameter."""
        from app.models.prediction import Prediction
        from decimal import Decimal
        
        # Create multiple predictions
        for i in range(15):
            pred = Prediction(
                model_name="test_model",
                model_version="v1.0",
                probability=Decimal(f"0.{i+10}"),
                risk_band="Medium",
                shap_json={},
            )
            db_session.add(pred)
        db_session.commit()
        
        # Request only 5 predictions
        response = client.get(
            "/predict/history",
            params={"limit": 5},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["predictions"]) <= 5
        # Total should still reflect all predictions
        assert data["total"] >= 15

    def test_prediction_history_ordered_by_most_recent(
        self, client: TestClient, auth_headers, db_session
    ):
        """Verify history returns predictions in descending order by predicted_at."""
        from app.models.prediction import Prediction
        from decimal import Decimal
        from datetime import datetime, timedelta, timezone
        
        # Create predictions with different timestamps
        base_time = datetime.now(timezone.utc)
        predictions = []
        for i in range(3):
            pred = Prediction(
                model_name="test_model",
                model_version="v1.0",
                probability=Decimal("0.50"),
                risk_band="Medium",
                shap_json={},
                predicted_at=base_time - timedelta(hours=i),
            )
            predictions.append(pred)
            db_session.add(pred)
        db_session.commit()
        
        # Fetch history
        response = client.get("/predict/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify order (most recent first)
        if len(data["predictions"]) >= 2:
            timestamps = [p["predicted_at"] for p in data["predictions"][:3]]
            # Timestamps should be in descending order
            assert timestamps == sorted(timestamps, reverse=True)
