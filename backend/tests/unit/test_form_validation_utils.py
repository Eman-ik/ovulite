"""Unit tests for chapter-specific form validation helpers."""

import pytest

from app.validation.common import validateEmail, validateRequiredFields


@pytest.mark.unit
class TestValidateEmail:
    def test_validate_email_with_valid_email(self):
        assert validateEmail("abc@gmail.com") is True

    def test_validate_email_with_invalid_email(self):
        assert validateEmail("abc.gmail.com") is False

    def test_validate_email_with_empty_string(self):
        assert validateEmail("") is False


@pytest.mark.unit
class TestValidateRequiredFields:
    def test_validate_required_fields_with_complete_data(self):
        payload = {
            "et_date": "2026-03-01",
            "cl_measure_mm": 18,
            "embryo_stage": 7,
        }
        required = ["et_date", "cl_measure_mm", "embryo_stage"]
        assert validateRequiredFields(payload, required) is True

    def test_validate_required_fields_with_missing_cl_size(self):
        payload = {
            "et_date": "2026-03-01",
            "cl_measure_mm": None,
            "embryo_stage": 7,
        }
        required = ["et_date", "cl_measure_mm", "embryo_stage"]
        assert validateRequiredFields(payload, required) is False
