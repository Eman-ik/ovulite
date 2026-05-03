"""Unit tests for model artifact directory resolution."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

import ml.config
import ml.predict


@pytest.mark.unit
def test_resolve_latest_valid_artifact_dir_prefers_newest_complete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Select the most recently modified complete version directory."""
    v1 = tmp_path / "v1"
    v2 = tmp_path / "v2"
    v1.mkdir()
    v2.mkdir()

    for version_dir in (v1, v2):
        (version_dir / "encoder_map.joblib").write_text("x", encoding="utf-8")
        (version_dir / "feature_names.json").write_text("[]", encoding="utf-8")
        (version_dir / "metadata.json").write_text("{}", encoding="utf-8")

    now = time.time()
    os.utime(v1, (now - 60, now - 60))
    os.utime(v2, (now, now))

    monkeypatch.setattr(ml.config, "ARTIFACTS_DIR", tmp_path)
    monkeypatch.setattr(ml.predict, "ARTIFACTS_DIR", tmp_path)

    resolved = ml.predict.PregnancyPredictor._resolve_latest_valid_artifact_dir()
    assert resolved.name == "v2"


@pytest.mark.unit
def test_resolve_latest_valid_artifact_dir_skips_incomplete_newer_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Skip incomplete latest dir and fallback to the latest complete one."""
    complete = tmp_path / "v_complete"
    incomplete = tmp_path / "v_incomplete"
    complete.mkdir()
    incomplete.mkdir()

    (complete / "encoder_map.joblib").write_text("x", encoding="utf-8")
    (complete / "feature_names.json").write_text("[]", encoding="utf-8")
    (complete / "metadata.json").write_text("{}", encoding="utf-8")

    # Missing metadata.json on purpose
    (incomplete / "encoder_map.joblib").write_text("x", encoding="utf-8")
    (incomplete / "feature_names.json").write_text("[]", encoding="utf-8")

    now = time.time()
    os.utime(complete, (now - 60, now - 60))
    os.utime(incomplete, (now, now))

    monkeypatch.setattr(ml.config, "ARTIFACTS_DIR", tmp_path)
    monkeypatch.setattr(ml.predict, "ARTIFACTS_DIR", tmp_path)

    resolved = ml.predict.PregnancyPredictor._resolve_latest_valid_artifact_dir()
    assert resolved.name == "v_complete"
