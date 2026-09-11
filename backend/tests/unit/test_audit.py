"""Tests for audit-trail construction.

The two properties that matter: nothing sensitive is ever written, and the
trail records what it actually observed rather than inventing an actor.
"""

import pytest

from app.services.audit import AUDITED_TABLES, _safe_detail


class TestRedaction:
    @pytest.mark.parametrize(
        "key", ["password", "Password", "password_hash", "token", "refresh_token", "api_key", "secret"]
    )
    def test_sensitive_keys_are_redacted(self, key):
        assert _safe_detail({key: "hunter2"})[key] == "[redacted]"

    def test_dict_values_are_reduced_to_their_keys(self):
        # Clinical values must not be copied into a log with a different
        # audience; the shape of the change is enough.
        out = _safe_detail({"payload": {"cl_measure_mm": 15.5, "bc_score": 3.0}})
        assert out["payload"] == ["bc_score", "cl_measure_mm"]

    def test_lists_are_stringified_and_capped(self):
        out = _safe_detail({"changed_fields": [f"f{i}" for i in range(80)]})
        assert len(out["changed_fields"]) == 50

    def test_scalars_pass_through(self):
        out = _safe_detail({"count": 3, "ok": True, "name": "donor", "missing": None})
        assert out == {"count": 3, "ok": True, "name": "donor", "missing": None}

    def test_empty_detail_is_none_not_an_empty_object(self):
        assert _safe_detail(None) is None
        assert _safe_detail({}) is None


class TestAuditedTables:
    def test_audit_table_is_not_itself_audited(self):
        # Auditing the audit would recurse on every write.
        assert "audit_events" not in AUDITED_TABLES

    def test_clinical_write_paths_are_covered(self):
        # Every table a clinical router mutates must be in the map, or those
        # writes are silently unaudited.
        for table in (
            "donors",
            "embryos",
            "recipients",
            "et_transfers",
            "opu_sessions",
            "ivf_batches",
            "pregnancy_checks",
            "calving_records",
            "users",
        ):
            assert table in AUDITED_TABLES, f"{table} is not audited"
