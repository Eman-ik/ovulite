"""Password strength policy.

One rule, enforced server-side everywhere a password is set: self-registration,
admin-created users, organization registration, password change and password
reset. The frontend shows the same rule, but this is what actually enforces it.
"""

import re

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128

PASSWORD_POLICY_MESSAGE = (
    f"Password must be at least {MIN_PASSWORD_LENGTH} characters and include an uppercase letter, "
    "a lowercase letter, a digit and a special character."
)


def password_problems(password: str) -> list[str]:
    """Return the list of policy rules the password breaks (empty = valid)."""
    problems = []
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        problems.append(f"at least {MIN_PASSWORD_LENGTH} characters")
    if isinstance(password, str) and len(password) > MAX_PASSWORD_LENGTH:
        problems.append(f"at most {MAX_PASSWORD_LENGTH} characters")
    if not re.search(r"[A-Z]", password or ""):
        problems.append("an uppercase letter")
    if not re.search(r"[a-z]", password or ""):
        problems.append("a lowercase letter")
    if not re.search(r"\d", password or ""):
        problems.append("a digit")
    if not re.search(r"[^A-Za-z0-9]", password or ""):
        problems.append("a special character")
    return problems


def validate_password_strength(password: str) -> str:
    """Pydantic-friendly validator: returns the password or raises ValueError."""
    problems = password_problems(password)
    if problems:
        raise ValueError(f"{PASSWORD_POLICY_MESSAGE} Missing: {', '.join(problems)}.")
    return password
