"""
Unit tests for Pydantic schema validation.

Tests:
- UT-7: CL measure range validation (5-35mm business rule, schema allows 0-50)
- UT-8: Enum validation (embryo_stage, protocol, CL side)
"""
import pytest
from decimal import Decimal
from pydantic import ValidationError

from app.schemas.et_transfer import ETTransferCreate, ETTransferBase


@pytest.mark.unit
class TestCLMeasureValidation:
    """Test CL (Corpus Luteum) size validation - UT-7"""

    def test_cl_size_accepts_valid_range(self):
        """UT-7: Test that CL size within 0-50mm is accepted (schema validation)"""
        valid_values = [Decimal("10.5"), Decimal("25.0"), Decimal("35.0"), Decimal("20.2")]
        
        for value in valid_values:
            # Should not raise ValidationError
            schema = ETTransferBase(
                et_date="2026-03-01",
                cl_measure_mm=value
            )
            assert schema.cl_measure_mm == value

    def test_cl_size_rejects_negative_value(self):
        """Test that negative CL size is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            ETTransferBase(
                et_date="2026-03-01",
                cl_measure_mm=Decimal("-5.0")
            )
        
        errors = exc_info.value.errors()
        assert any("between 0 and 50" in str(e) for e in errors)

    def test_cl_size_rejects_value_above_maximum(self):
        """Test that CL size above 50mm is rejected"""
        with pytest.raises(ValidationError) as exc_info:
            ETTransferBase(
                et_date="2026-03-01",
                cl_measure_mm=Decimal("55.0")
            )
        
        errors = exc_info.value.errors()
        assert any("between 0 and 50" in str(e) for e in errors)

    def test_cl_size_accepts_null_value(self):
        """Test that missing/null CL size is accepted (optional field)"""
        schema = ETTransferBase(
            et_date="2026-03-01",
            cl_measure_mm=None
        )
        assert schema.cl_measure_mm is None

    def test_cl_size_accepts_boundary_values(self):
        """Test boundary values 0 and 50"""
        # Minimum boundary
        schema_min = ETTransferBase(
            et_date="2026-03-01",
            cl_measure_mm=Decimal("0")
        )
        assert schema_min.cl_measure_mm == Decimal("0")
        
        # Maximum boundary
        schema_max = ETTransferBase(
            et_date="2026-03-01",
            cl_measure_mm=Decimal("50")
        )
        assert schema_max.cl_measure_mm == Decimal("50")


@pytest.mark.unit
class TestCLSideValidation:
    """Test CL side laterality validation - UT-8"""

    def test_cl_side_accepts_left(self):
        """Test that 'Left' is accepted for CL side"""
        schema = ETTransferBase(
            et_date="2026-03-01",
            cl_side="Left"
        )
        assert schema.cl_side == "Left"

    def test_cl_side_accepts_right(self):
        """Test that 'Right' is accepted for CL side"""
        schema = ETTransferBase(
            et_date="2026-03-01",
            cl_side="Right"
        )
        assert schema.cl_side == "Right"

    def test_cl_side_rejects_invalid_value(self):
        """UT-8: Test that invalid CL side values are rejected"""
        invalid_values = ["left", "right", "LEFT", "CENTER", "middle", "both"]
        
        for invalid_value in invalid_values:
            with pytest.raises(ValidationError) as exc_info:
                ETTransferBase(
                    et_date="2026-03-01",
                    cl_side=invalid_value
                )
            
            errors = exc_info.value.errors()
            assert any("Left" in str(e) and "Right" in str(e) for e in errors)

    def test_cl_side_accepts_null(self):
        """Test that null/missing CL side is accepted"""
        schema = ETTransferBase(
            et_date="2026-03-01",
            cl_side=None
        )
        assert schema.cl_side is None


@pytest.mark.unit
class TestPC1ResultValidation:
    """Test pregnancy check result validation - UT-8"""

    def test_pc1_result_accepts_valid_values(self):
        """Test that valid PC1 result values are accepted"""
        valid_values = ["Pregnant", "Open", "Recheck"]
        
        for value in valid_values:
            schema = ETTransferBase(
                et_date="2026-03-01",
                pc1_result=value
            )
            assert schema.pc1_result == value

    def test_pc1_result_rejects_invalid_values(self):
        """Test that invalid PC1 result values are rejected"""
        invalid_values = ["pregnant", "open", "PREGNANT", "Unknown", "TBD", "positive"]
        
        for invalid_value in invalid_values:
            with pytest.raises(ValidationError) as exc_info:
                ETTransferBase(
                    et_date="2026-03-01",
                    pc1_result=invalid_value
                )
            
            errors = exc_info.value.errors()
            assert any("Pregnant" in str(e) or "Open" in str(e) for e in errors)

    def test_pc1_result_accepts_null(self):
        """Test that null PC1 result is accepted (optional field)"""
        schema = ETTransferBase(
            et_date="2026-03-01",
            pc1_result=None
        )
        assert schema.pc1_result is None


@pytest.mark.unit
class TestDateValidation:
    """Test date field validation"""

    def test_et_date_required(self):
        """Test that et_date is a required field"""
        with pytest.raises(ValidationError) as exc_info:
            ETTransferBase()
        
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("et_date",) for e in errors)

    def test_et_date_accepts_valid_date_string(self):
        """Test that valid date strings are accepted and parsed"""
        schema = ETTransferBase(et_date="2026-03-15")
        assert str(schema.et_date) == "2026-03-15"

    def test_et_date_rejects_invalid_format(self):
        """Test that invalid date formats are rejected"""
        invalid_dates = ["15/03/2026", "2026-15-03", "not-a-date", "03-15-2026"]
        
        for invalid_date in invalid_dates:
            with pytest.raises(ValidationError):
                ETTransferBase(et_date=invalid_date)
