"""Validation helper utilities used by tests and API business rules."""

from __future__ import annotations

import re
from typing import Any

_EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def validate_email(value: str) -> bool:
    """Return True when the value is a syntactically valid email address."""
    if not isinstance(value, str) or value.strip() == "":
        return False
    return _EMAIL_PATTERN.match(value.strip()) is not None


def validate_required_fields(payload: dict[str, Any], required_fields: list[str]) -> bool:
    """Return True only when all required fields exist and are non-empty."""
    for field_name in required_fields:
        value = payload.get(field_name)
        if value is None:
            return False
        if isinstance(value, str) and value.strip() == "":
            return False
    return True


# Chapter-aligned aliases

def validateEmail(value: str) -> bool:  # noqa: N802
    return validate_email(value)


def validateRequiredFields(payload: dict[str, Any], required_fields: list[str]) -> bool:  # noqa: N802
    return validate_required_fields(payload, required_fields)
