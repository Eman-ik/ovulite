"""The four-role vocabulary: legacy strings map onto it, unknown strings fail closed,
and researcher can never write clinical or lab data."""

import pytest

from app.auth.dependencies import (
    ADMIN_ROLES,
    CANONICAL_ROLES,
    ET_WRITE_ROLES,
    LAB_WRITE_ROLES,
    PREDICTION_RUN_ROLES,
    normalize_role,
)


def test_there_are_exactly_four_roles():
    assert CANONICAL_ROLES == ("admin", "embryologist", "veterinarian", "researcher")


@pytest.mark.parametrize("legacy, expected", [
    ("organization_admin", "admin"),
    ("organization admin", "admin"),
    ("et team", "veterinarian"),
    ("et-team", "veterinarian"),
    ("et_team", "veterinarian"),
    ("viewer", "researcher"),
    ("  Admin  ", "admin"),
])
def test_legacy_strings_map_to_their_job(legacy, expected):
    assert normalize_role(legacy) == expected


@pytest.mark.parametrize("unknown", ["superuser", "root", "", None, "technical_staff"])
def test_unknown_roles_fail_closed(unknown):
    # An unrecognised role must not be guessed into a real one.
    assert normalize_role(unknown) is None


def test_admin_roles_is_admin_only():
    assert ADMIN_ROLES == ("admin",)


def test_researcher_is_in_no_write_group():
    for group in (LAB_WRITE_ROLES, ET_WRITE_ROLES):
        assert "researcher" not in group
    assert "researcher" not in PREDICTION_RUN_ROLES


def test_each_write_group_is_exactly_the_job_it_names():
    assert set(LAB_WRITE_ROLES) == {"admin", "embryologist"}
    assert set(ET_WRITE_ROLES) == {"admin", "veterinarian"}
    # Recording an outcome is ET-side; the embryologist may only run a prediction.
    assert "embryologist" not in ET_WRITE_ROLES
    assert "embryologist" in PREDICTION_RUN_ROLES
