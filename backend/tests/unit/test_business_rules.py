"""Risk-band thresholds.

Bands are Low / Moderate / High at 0.35 and 0.65, matching both ml.config
RISK_BANDS and the deployed artifact's risk_band_thresholds. These tests
previously asserted 0.30 / 0.60 and the label "Medium", which no code has ever
produced.

At runtime ``Predictor.predict`` passes the *artifact's* thresholds, not the
module default, so the two must agree or the served band stops matching the
documented one. test_artifact_thresholds_match_code_default pins that.
"""

import json
from pathlib import Path

import pytest

from ml.config import ARTIFACTS_DIR, RISK_BANDS, get_risk_band


@pytest.mark.unit
@pytest.mark.parametrize(
    "probability,expected",
    [
        (0.0, "Low"),
        (0.29, "Low"),
        (0.3499, "Low"),
        (0.35, "Moderate"),   # low_max is inclusive of the Moderate band
        (0.45, "Moderate"),
        (0.60, "Moderate"),
        (0.6499, "Moderate"),
        (0.65, "High"),       # high_min is inclusive of the High band
        (0.80, "High"),
        (1.0, "High"),
    ],
)
def test_risk_band_boundaries(probability, expected):
    assert get_risk_band(probability) == expected


@pytest.mark.unit
def test_explicit_thresholds_override_the_default():
    bands = {"low_max": 0.10, "high_min": 0.20}
    assert get_risk_band(0.05, bands) == "Low"
    assert get_risk_band(0.15, bands) == "Moderate"
    assert get_risk_band(0.25, bands) == "High"


@pytest.mark.unit
def test_no_artifact_declares_thresholds_that_differ_from_code():
    """No artifact may pin bands that disagree with RISK_BANDS.

    This is the desync the stale tests were hiding: predict() passes the
    artifact's thresholds, so a change to one side alone silently re-bands every
    served prediction. An artifact that omits the key is fine — get_risk_band
    falls back to the module default — so only declared values are checked.
    """
    declared = {
        path.parent.name: json.loads(path.read_text(encoding="utf-8")).get("risk_band_thresholds")
        for path in ARTIFACTS_DIR.glob("v*/metadata.json")
    }
    mismatched = {
        name: value
        for name, value in declared.items()
        if value is not None and value != RISK_BANDS
    }
    assert not mismatched, f"artifacts disagree with ml.config {RISK_BANDS}: {mismatched}"
