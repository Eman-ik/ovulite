"""The model-integrity badge must mean the files match the manifest, not merely that it exists."""

import hashlib
import json
import tempfile
from pathlib import Path

from app.api.predictions import _manifest_matches
from ml.config import ARTIFACTS_DIR

# The cached wrapper would remember the first answer for a folder, so the
# tamper checks call the underlying function. tempfile rather than pytest's
# tmp_path, whose root is not writable in this environment.
_check = _manifest_matches.__wrapped__


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_deployed_artifacts_match_their_manifest():
    assert _manifest_matches(str(ARTIFACTS_DIR / "v1.0.0")) is True


def test_changed_file_fails_the_check():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "model.bin").write_bytes(b"original")
        (base / "manifest.json").write_text(json.dumps({"files": {"model.bin": _sha(b"original")}}))
        assert _check(str(base)) is True

        (base / "model.bin").write_bytes(b"swapped")
        assert _check(str(base)) is False


def test_missing_file_fails_the_check():
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "manifest.json").write_text(json.dumps({"files": {"model.bin": _sha(b"x")}}))
        assert _check(str(base)) is False
