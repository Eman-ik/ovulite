"""Unit tests for business-rule confidence level thresholds."""

import pytest

from ml.config import get_risk_band


@pytest.mark.unit
def test_risk_band_high_when_probability_above_point_six():
    assert get_risk_band(0.61) == "High"


@pytest.mark.unit
def test_risk_band_medium_when_probability_equals_point_six():
    assert get_risk_band(0.6) == "Medium"


@pytest.mark.unit
def test_risk_band_medium_when_probability_between_point_three_and_point_six():
    assert get_risk_band(0.45) == "Medium"


@pytest.mark.unit
def test_risk_band_low_when_probability_below_point_three():
    assert get_risk_band(0.29) == "Low"
