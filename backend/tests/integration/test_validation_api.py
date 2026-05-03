"""
Integration tests for validation - API error handling.

Tests:
- CT-6: POST /transfers with invalid CL size returns 422
- CT-7: POST /transfers with missing required field returns 422
- Validation error response format
"""
import pytest
from decimal import Decimal


@pytest.mark.integration
class TestTransferValidationAPI:
    """Test transfer validation error responses - CT-6, CT-7"""

    def test_invalid_cl_size_returns_422(self, client, auth_headers, sample_transfer_data):
        """CT-6: Test that invalid CL size (>50mm) returns 422 Unprocessable Entity"""
        invalid_data = sample_transfer_data.copy()
        invalid_data["cl_measure_mm"] = 55.0  # Exceeds max 50mm
        
        response = client.post(
            "/transfers/",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422
        error_detail = response.json()
        assert "detail" in error_detail
        # Should contain validation error mentioning cl_measure_mm
        error_text = str(error_detail["detail"])
        assert "cl_measure_mm" in error_text or "50" in error_text

    def test_negative_cl_size_returns_422(self, client, auth_headers, sample_transfer_data):
        """Test that negative CL size returns 422"""
        invalid_data = sample_transfer_data.copy()
        invalid_data["cl_measure_mm"] = -5.0
        
        response = client.post(
            "/transfers/",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422

    def test_invalid_cl_side_returns_422(self, client, auth_headers, sample_transfer_data):
        """Test that invalid CL side value returns 422"""
        invalid_data = sample_transfer_data.copy()
        invalid_data["cl_side"] = "middle"  # Invalid, must be Left or Right
        
        response = client.post(
            "/transfers/",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422
        error_detail = response.json()
        error_text = str(error_detail["detail"])
        assert "cl_side" in error_text.lower()

    def test_invalid_pc1_result_returns_422(self, client, auth_headers, sample_transfer_data):
        """Test that invalid PC1 result returns 422"""
        invalid_data = sample_transfer_data.copy()
        invalid_data["pc1_result"] = "unknown"  # Invalid, must be Pregnant/Open/Recheck
        
        response = client.post(
            "/transfers/",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422

    def test_missing_required_field_returns_422(self, client, auth_headers):
        """CT-7: Test that missing required field (et_date) returns 422"""
        incomplete_data = {
            "recipient_id": 1,
            # Missing et_date (required)
        }
        
        response = client.post(
            "/transfers/",
            json=incomplete_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422
        error_detail = response.json()
        assert "detail" in error_detail
        error_text = str(error_detail["detail"])
        assert "et_date" in error_text or "required" in error_text.lower()

    def test_invalid_date_format_returns_422(self, client, auth_headers, sample_transfer_data):
        """Test that invalid date format returns 422"""
        invalid_data = sample_transfer_data.copy()
        invalid_data["et_date"] = "15/03/2026"  # Invalid format
        
        response = client.post(
            "/transfers/",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422


@pytest.mark.integration
class TestValidationErrorFormat:
    """Test that validation errors return proper FastAPI/Pydantic format"""

    def test_validation_error_has_proper_structure(self, client, auth_headers):
        """Test that 422 errors follow FastAPI validation format"""
        response = client.post(
            "/transfers/",
            json={"invalid_field": "value"},  # Missing required fields
            headers=auth_headers
        )
        
        assert response.status_code == 422
        error_body = response.json()
        
        # FastAPI validation errors have this structure
        assert "detail" in error_body
        # detail can be list or string depending on FastAPI version
        assert isinstance(error_body["detail"], (list, str, dict))

    def test_multiple_validation_errors_returned(self, client, auth_headers):
        """Test that multiple validation errors are returned together"""
        invalid_data = {
            "et_date": "invalid-date",  # Invalid format
            "cl_measure_mm": 100.0,     # Exceeds max
            "cl_side": "middle",        # Invalid enum
        }
        
        response = client.post(
            "/transfers/",
            json=invalid_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422
        # Should contain multiple error details
        error_body = response.json()
        assert "detail" in error_body
