"""JWT token creation/verification and password hashing utilities."""

import hashlib
import logging
import os
import re
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt  # PyJWT â€” replaces python-jose, which has unfixed CVEs
from fastapi import HTTPException, status
from jwt import PyJWTError as JWTError
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

_INSECURE_DEFAULT_SECRET = "change-me-in-production-use-openssl-rand-hex-32"
_configured_secret = os.getenv("SECRET_KEY")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
MIN_SECRET_LENGTH = 32


def _secret_problem(secret: str) -> str | None:
    """Why a signing key is definitely unsafe, or None.

    Anyone who knows the key can mint a token for any user and any role, so
    production refuses to start on these.
    """
    if secret == _INSECURE_DEFAULT_SECRET:
        return "it is the documented placeholder"
    if len(secret) < MIN_SECRET_LENGTH:
        return f"it is shorter than {MIN_SECRET_LENGTH} characters"
    if len(set(secret)) < 12:
        return "it has too few distinct characters"
    return None


def _secret_looks_like_phrase(secret: str) -> bool:
    """Heuristic warning only: readable phrases ("ovulite-local-secret-2026")
    are easy to guess. Never used to refuse startup â€” no heuristic can tell
    every random key from a phrase, and a false positive that blocks a deploy
    is worse than a log line."""
    chunks = re.split(r"[-_ .:/]+", secret)
    plain_words = [c for c in chunks if re.fullmatch(r"[a-z]{3,}|[A-Z][a-z]{2,}", c)]
    camel_phrase = any(
        all(re.search(r"[aeiou]", w) for w in re.findall(r"[A-Z][a-z]{3,}", run))
        for run in re.findall(r"(?:[A-Z][a-z]{3,}){3,}", secret)
    )
    return len(plain_words) >= 3 or camel_phrase


if not _configured_secret:
    if ENVIRONMENT == "production":
        raise RuntimeError(
            "SECRET_KEY is not set. Per NFR-SEC-05, secrets must come from environment/secrets "
            "management, not source defaults â€” refusing to start in production without one. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    logger.warning(
        "SECRET_KEY is not set; using the documented development placeholder. "
        "This is only safe outside production â€” set a real SECRET_KEY in .env before deploying."
    )
    _configured_secret = _INSECURE_DEFAULT_SECRET
else:
    _problem = _secret_problem(_configured_secret)
    if _problem and ENVIRONMENT == "production":
        raise RuntimeError(
            f"SECRET_KEY is unsafe ({_problem}) while ENVIRONMENT=production. Generate a real "
            "secret with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    if _problem:
        logger.warning("SECRET_KEY is unsafe (%s); fine for local testing only.", _problem)
    elif _secret_looks_like_phrase(_configured_secret):
        logger.warning(
            "SECRET_KEY looks like a readable phrase, which is easy to guess. Replace it with "
            "python -c \"import secrets; print(secrets.token_hex(32))\""
        )

SECRET_KEY = _configured_secret
ALGORITHM = os.getenv("ALGORITHM", "HS256")
# Allowlisted rather than passed through: "none" would make every token
# forgeable, and an RS* value here with an HMAC key is the classic confusion bug.
if ALGORITHM not in ("HS256", "HS384", "HS512"):
    raise RuntimeError("ALGORITHM must be one of HS256, HS384, HS512")

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

IS_PRODUCTION = ENVIRONMENT == "production"

# Account lockout.
MAX_FAILED_LOGIN_ATTEMPTS = int(os.getenv("MAX_FAILED_LOGIN_ATTEMPTS", "5"))
LOCKOUT_DURATION_MINUTES = int(os.getenv("LOCKOUT_DURATION_MINUTES", "15"))

# Per-IP ceiling on FAILED logins per minute. The per-account lockout does not
# stop one client from trying one password against many accounts.
MAX_FAILED_LOGINS_PER_IP_PER_MINUTE = int(os.getenv("MAX_FAILED_LOGINS_PER_IP_PER_MINUTE", "30"))

# Password-reset token lifetime.
RESET_TOKEN_EXPIRE_MINUTES = int(os.getenv("RESET_TOKEN_EXPIRE_MINUTES", "30"))

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password using argon2."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against an argon2 hash."""
    return pwd_context.verify(plain, hashed)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token with the given payload and expiry."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    # `iat` is what lets a password change invalidate tokens minted before it.
    to_encode.update({
        "exp": expire,
        "iat": int(time.time()),
        "type": "access",
        "jti": str(uuid.uuid4()),
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT refresh token with longer expiry."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({
        "exp": expire,
        "iat": int(time.time()),
        "type": "refresh",
        "jti": str(uuid.uuid4()),
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str, token_type: str = "access") -> dict[str, Any]:
    """Decode and validate a JWT. Raises 401 on any failure."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("sub") is None:
            raise credentials_exception
        # Verify token type matches expected
        if payload.get("type") != token_type:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception


def decode_token_unverified_type(token: str) -> dict[str, Any] | None:
    """Decode a JWT (signature and expiry still checked) whatever its type.
    Returns None instead of raising, for callers that are revoking rather than
    authenticating."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# â”€â”€ Account lockout â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def is_account_locked(locked_until: datetime | None) -> bool:
    """True if the account is currently inside its lockout window."""
    if locked_until is None:
        return False
    if locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) < locked_until


def compute_lockout_after_failed_attempt(failed_count: int) -> tuple[int, datetime | None]:
    """Given the failed-attempt count *before* this failure, return the new
    count and a ``locked_until`` timestamp once the threshold is reached."""
    new_count = (failed_count or 0) + 1
    if new_count >= MAX_FAILED_LOGIN_ATTEMPTS:
        return new_count, datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
    return new_count, None


# â”€â”€ Password reset tokens â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def generate_reset_token() -> tuple[str, datetime]:
    """A cryptographically random reset token and its expiry."""
    return (
        secrets.token_urlsafe(32),
        datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES),
    )


def hash_reset_token(token: str) -> str:
    """SHA-256 of a reset token. Only this is stored, so a leaked database row
    cannot be used to reset someone's password. Plain SHA-256 rather than
    argon2 because the token is 256 bits of entropy already â€” there is nothing
    to brute-force â€” and reset has to look the row up by value."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# â”€â”€ Session invalidation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def issued_before_password_change(
    payload: dict[str, Any], sessions_valid_after: datetime | None
) -> bool:
    """True when a token predates the user's last password change or explicit
    session revocation.

    This is what makes "change your password" and "log out everywhere"
    actually end a session an attacker already holds, rather than leaving it
    alive until the token expires on its own.
    """
    if sessions_valid_after is None:
        return False
    if sessions_valid_after.tzinfo is None:
        sessions_valid_after = sessions_valid_after.replace(tzinfo=timezone.utc)
    issued = payload.get("iat")
    if issued is None:
        return True  # minted before `iat` was added: cannot prove it is current
    return int(issued) < int(sessions_valid_after.timestamp())


def revocation_stamp() -> datetime:
    """A ``sessions_revoked_at`` value that reliably kills tokens issued right now.

    JWT ``iat`` is whole seconds and the check above is "issued strictly
    before the stamp", so stamping the current instant leaves a token minted
    in the same second alive — which made "log out everywhere" silently do
    nothing when called moments after logging in. One second into the future
    closes that window.

    Only for paths that issue NO replacement token. A future stamp cannot be
    paired with a freshly minted one: PyJWT refuses a token whose ``iat`` is
    ahead of the clock (ImmatureSignatureError). Those paths stamp the current
    second and revoke the caller's old token by jti instead.
    """
    return datetime.now(timezone.utc) + timedelta(seconds=1)
