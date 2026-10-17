"""Authentication API endpoints — login, register, seed, me.

Security rules enforced here:

* Signup can never choose its own role or organization. Before this,
  ``POST /auth/register`` was unauthenticated and copied ``role`` straight out
  of the request body, so anyone who could reach the API could make themselves
  an admin. Self-registered accounts now get the lowest-privilege role and,
  unless REQUIRE_SIGNUP_APPROVAL=false, wait for an administrator.
* Five wrong passwords lock an account for fifteen minutes, and a per-IP
  ceiling stops one client walking through many accounts.
* Changing or resetting a password, and "log out everywhere", end every
  session opened earlier — including one an attacker already holds.
* Refresh tokens rotate and are single-use; replaying one ends every session
  for that account, because a replay means someone has a copy.
"""

import logging
import os
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

from fastapi import Request, APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, oauth2_scheme
from app.auth.security import (
    ENVIRONMENT,
    IS_PRODUCTION,
    MAX_FAILED_LOGINS_PER_IP_PER_MINUTE,
    RESET_TOKEN_EXPIRE_MINUTES,
    compute_lockout_after_failed_attempt,
    create_access_token,
    create_refresh_token,
    decode_token_unverified_type,
    generate_reset_token,
    hash_password,
    hash_reset_token,
    is_account_locked,
    issued_before_password_change,
    revocation_stamp,
    verify_password,
    verify_token,
)
from app.database import get_db
from app.models.token_blacklist import RevokedToken
from app.database import SessionLocal
from app.models.audit_event import (
    AUTH_LOGIN_FAILURE,
    AUTH_LOGIN_SUCCESS,
    AUTH_LOGOUT,
    OUTCOME_DENIED,
    OUTCOME_FAILURE,
)
from app.models.user import User
from app.services.audit import record, record_auth
from app.models.organization import Organization, OrganizationMembership
from app.schemas.organization import OrganizationRegistrationRequest, OrganizationRegistrationResponse
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    GoogleAuthRequest,
    LogoutRequest,
    LogoutResponse,
    RefreshTokenRequest,
    RegisterResponse,
    ResetPasswordRequest,
    TokenResponse,
)
from app.schemas.user import UserCreate, UserResponse

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

logger = logging.getLogger(__name__)

router = APIRouter()


def _flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes")


# The role a self-registered account gets. Never taken from the request.
SELF_REGISTER_ROLE = "researcher"
PENDING_MESSAGE = "Your account is waiting for an administrator to approve it."

# Signup approval is on by default. The flag exists so a demo can be run
# without an admin in the loop; it does NOT re-open the role hole — a
# self-registered account is always SELF_REGISTER_ROLE either way.
REQUIRE_SIGNUP_APPROVAL = _flag("REQUIRE_SIGNUP_APPROVAL", default=True)

# Bootstrap admin password. In production it must come from the environment,
# and an explicitly provisioned one must be changed at first login. Outside
# production the documented development password is kept as-is, because
# CLAUDE.md documents it and the demo logins depend on it.
DEV_DEFAULT_ADMIN_PASSWORD = "ovulite2026"
_ENV_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD")
DEFAULT_ADMIN_PASSWORD = _ENV_ADMIN_PASSWORD or (None if IS_PRODUCTION else DEV_DEFAULT_ADMIN_PASSWORD)


# ── Per-IP failed-login throttle ───────────────────────────────────────────
# The account lockout protects one account. This protects against one client
# trying one password against many accounts. In-memory, so it is per process —
# a shared store would be needed to make it hold across replicas.
_FAILED_LOGINS: dict[str, deque] = defaultdict(deque)
_FAILED_WINDOW_SECONDS = 60


def _client_ip(request: Request | None) -> str:
    if request is None:
        return "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _too_many_failed_logins(ip: str) -> bool:
    bucket = _FAILED_LOGINS[ip]
    now = time.time()
    while bucket and now - bucket[0] > _FAILED_WINDOW_SECONDS:
        bucket.popleft()
    return len(bucket) >= MAX_FAILED_LOGINS_PER_IP_PER_MINUTE


def _record_failed_login(ip: str) -> None:
    _FAILED_LOGINS[ip].append(time.time())


def _revoke(db: Session, payload: dict | None) -> bool:
    """Add a decoded token's jti to the revocation list. True if a new row was
    written."""
    if not payload:
        return False
    jti, exp = payload.get("jti"), payload.get("exp")
    if not jti or not exp:
        return False
    if db.query(RevokedToken).filter(RevokedToken.jti == jti).first():
        return False
    db.add(RevokedToken(
        jti=jti,
        expires_at=datetime.fromtimestamp(int(exp), tz=timezone.utc),
        revoked_at=datetime.now(timezone.utc),
    ))
    return True


def _set_password(user: User, new_password: str) -> None:
    """Set a password and clear everything that depended on the old one.

    password_changed_at is what ends sessions opened with the old password,
    so it must be stamped here and not left to the caller.
    """
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    user.password_changed_at = datetime.now(timezone.utc)
    user.reset_token = None
    user.reset_token_expires = None
    user.failed_login_count = 0
    user.locked_until = None


def ensure_default_organization(db: Session) -> Organization:
    """Create the default bootstrap organization if it does not exist."""
    organization = (
        db.query(Organization)
        .filter(func.lower(Organization.slug) == "ovulite-default")
        .first()
    )
    if organization:
        return organization

    organization = Organization(
        name="Ovulite Default Organization",
        slug="ovulite-default",
        organization_type="lab",
        country="PK",
        time_zone="Asia/Karachi",
        primary_species="Cattle",
    )
    db.add(organization)
    db.commit()
    db.refresh(organization)
    logger.info("Default organization seeded")
    return organization


def ensure_default_admin(db: Session) -> bool:
    """Create the default admin user if the database is empty.

    Returns True when a new admin user was created, False otherwise.
    """
    user_count = db.query(User).count()
    if user_count > 0:
        return False

    if not DEFAULT_ADMIN_PASSWORD:
        # Production with nothing configured: refuse rather than create an
        # account whose password is written in this repository.
        logger.warning(
            "No users exist and DEFAULT_ADMIN_PASSWORD is not set; skipping admin bootstrap. "
            "Set DEFAULT_ADMIN_PASSWORD to create the first admin."
        )
        return False

    organization = ensure_default_organization(db)

    admin = User(
        organization_id=organization.organization_id,
        username="admin",
        password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
        role="admin",
        full_name="System Administrator",
        # An explicitly provisioned password is a hand-off credential and must
        # be replaced. The documented development default is left alone: it is
        # in CLAUDE.md and the demo logins depend on it.
        must_change_password=bool(_ENV_ADMIN_PASSWORD),
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    membership = OrganizationMembership(
        organization_id=organization.organization_id,
        user_id=admin.user_id,
        role="admin",
        status="active",
        is_primary=True,
    )
    db.add(membership)
    db.commit()

    logger.info("Default admin user seeded")
    return True


@router.post("/login", response_model=TokenResponse)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate a user and return a JWT access token.

    Accepts OAuth2-compatible form data (username + password fields).
    """
    ip = _client_ip(request)
    if _too_many_failed_logins(ip):
        record_auth(
            SessionLocal, AUTH_LOGIN_FAILURE, actor_label=form_data.username.strip()[:100],
            outcome=OUTCOME_DENIED, message="Per-IP failed-login throttle", request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts from this address. Try again in a minute.",
        )

    login_value = form_data.username.strip()
    user = (
        db.query(User)
        .filter(
            or_(
                func.lower(User.username) == func.lower(login_value),
                func.lower(User.email) == func.lower(login_value),
            )
        )
        .first()
    )

    # An expired lock starts the user with a clean slate.
    if user is not None and user.locked_until is not None and not is_account_locked(user.locked_until):
        user.failed_login_count = 0
        user.locked_until = None
        db.commit()

    # Checked BEFORE the password, so the lockout window cannot be used as an
    # oracle to keep testing passwords against a locked account.
    if user is not None and is_account_locked(user.locked_until):
        record_auth(
            SessionLocal, AUTH_LOGIN_FAILURE, actor=user, actor_label=login_value,
            outcome=OUTCOME_DENIED, message="Account locked", request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account temporarily locked after too many failed login attempts. Try again later.",
        )

    if user is None or not verify_password(form_data.password, user.password_hash):
        _record_failed_login(ip)
        locked_now = None
        if user is not None:
            new_count, locked_now = compute_lockout_after_failed_attempt(user.failed_login_count)
            user.failed_login_count = new_count
            user.locked_until = locked_now
            db.commit()
            if locked_now is not None:
                logger.warning("User '%s' locked out after %d failed attempts", user.username, new_count)
        # Recorded on its own session: a failed login has no successful
        # transaction to ride along with, and it is the event most worth
        # keeping. The attempted identifier is kept; the password never is.
        record_auth(
            SessionLocal,
            AUTH_LOGIN_FAILURE,
            actor=user,
            actor_label=login_value,
            outcome=OUTCOME_FAILURE,
            message=(
                "Unknown user" if user is None
                else ("Bad password — account now locked" if locked_now else "Bad password")
            ),
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # The password was correct, so it is safe to say why the login is refused
    # without telling an attacker anything they could not already confirm.
    if user.pending_approval:
        record_auth(
            SessionLocal, AUTH_LOGIN_FAILURE, actor=user, actor_label=login_value,
            outcome=OUTCOME_DENIED, message="Awaiting admin approval", request=request,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=PENDING_MESSAGE)

    if not user.active:
        record_auth(
            SessionLocal,
            AUTH_LOGIN_FAILURE,
            actor=user,
            actor_label=login_value,
            outcome=OUTCOME_DENIED,
            message="Account is disabled",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login = datetime.now(timezone.utc)
    record(db, AUTH_LOGIN_SUCCESS, actor=user, target_type="user",
           target_id=user.user_id, request=request)
    db.commit()

    logger.info("User '%s' logged in successfully", user.username)
    return _issue_tokens_for(user)


# Two browser tabs can refresh within moments of each other with the same
# stored token. That is not an attack, so a replay this soon after the first
# use is refused without ending every session.
REFRESH_REUSE_GRACE_SECONDS = 30


@router.post("/refresh", response_model=TokenResponse)
def refresh_access_token(
    request: Request,
    payload: RefreshTokenRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Exchange a refresh token for a NEW access token and a NEW refresh token.

    Rotation: the presented token is revoked, so each refresh token works once.
    Reuse detection: an already-used refresh token coming back later means
    someone holds a copy, so every session for that account is ended.

    The caller MUST store the returned refresh_token — the one it sent is dead.
    """
    token_payload = verify_token(payload.refresh_token, token_type="refresh")
    username = token_payload.get("sub")
    user = db.query(User).filter(func.lower(User.username) == func.lower(username or "")).first()

    refresh_jti = token_payload.get("jti")
    revoked = db.query(RevokedToken).filter(RevokedToken.jti == refresh_jti).first() if refresh_jti else None
    if revoked is not None:
        revoked_at = revoked.revoked_at if revoked.revoked_at.tzinfo else revoked.revoked_at.replace(tzinfo=timezone.utc)
        if user is not None and (datetime.now(timezone.utc) - revoked_at).total_seconds() > REFRESH_REUSE_GRACE_SECONDS:
            user.sessions_revoked_at = revocation_stamp()
            db.commit()
            record_auth(
                SessionLocal, AUTH_LOGIN_FAILURE, actor=user, actor_label=user.username,
                outcome=OUTCOME_DENIED,
                message="Refresh token reused — all sessions ended", request=request,
            )
            logger.warning("Refresh token reuse for '%s': all sessions ended", user.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    if user is None or not user.active or user.pending_approval:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    if issued_before_password_change(token_payload, user.sessions_valid_after):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has ended. Log in again.",
        )

    _revoke(db, token_payload)
    db.commit()
    logger.info("Refreshed tokens for user '%s'", user.username)
    return _issue_tokens_for(user)


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(
    request: Request,
    payload: UserCreate,
    db: Session = Depends(get_db),
) -> RegisterResponse:
    """Public signup.

    The account is always created with SELF_REGISTER_ROLE in the default
    organization, and (unless REQUIRE_SIGNUP_APPROVAL=false) cannot log in
    until an administrator approves it.

    ``payload.role`` and ``payload.organization_id`` are ignored on purpose.
    This endpoint is unauthenticated, and it previously passed both straight
    through to the new row — so a stranger could POST role="admin" here, log
    in, and reach every admin-gated endpoint. An admin creates privileged
    accounts through POST /admin/users, which is admin-only.
    """
    if db.query(User).filter(func.lower(User.username) == func.lower(payload.username)).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{payload.username}' already exists",
        )
    if payload.email and db.query(User).filter(func.lower(User.email) == func.lower(payload.email)).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    organization_id = ensure_default_organization(db).organization_id
    if payload.organization_id is not None and payload.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Self-registration cannot join another organization.",
        )

    user = User(
        organization_id=organization_id,
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=SELF_REGISTER_ROLE,
        full_name=payload.full_name,
        email=payload.email,
        pending_approval=REQUIRE_SIGNUP_APPROVAL,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    membership = OrganizationMembership(
        organization_id=organization_id,
        user_id=user.user_id,
        role=SELF_REGISTER_ROLE,
        status="pending" if REQUIRE_SIGNUP_APPROVAL else "active",
        is_primary=False,
    )
    db.add(membership)
    db.commit()

    if payload.role and payload.role != SELF_REGISTER_ROLE:
        logger.warning(
            "Signup for '%s' asked for role '%s'; ignored and created as '%s'",
            user.username, payload.role, SELF_REGISTER_ROLE,
        )
    record_auth(
        SessionLocal, AUTH_LOGIN_SUCCESS, actor=user, actor_label=user.username,
        message=f"Signed up as {SELF_REGISTER_ROLE}"
                + (" — awaiting approval" if REQUIRE_SIGNUP_APPROVAL else ""),
        request=request,
    )
    logger.info("User '%s' registered as '%s'", user.username, user.role)

    return RegisterResponse(
        message=(
            "Account created. An administrator must approve it before you can log in."
            if REQUIRE_SIGNUP_APPROVAL
            else "Account created. You can log in now."
        ),
        username=user.username,
        pending_approval=REQUIRE_SIGNUP_APPROVAL,
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Return the currently authenticated user's profile."""
    return current_user


@router.post("/logout", response_model=LogoutResponse)
def logout(
    request: Request,
    payload: LogoutRequest | None = None,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LogoutResponse:
    """Revoke the caller's access token immediately, rather than waiting for
    it to expire — and the refresh token too when one is sent.

    Revoking only the access token left the refresh token usable for days,
    so "log out" did not end the session.
    """
    revoked = 0
    if _revoke(db, decode_token_unverified_type(token)):
        revoked += 1
    if payload and payload.refresh_token:
        refresh_payload = decode_token_unverified_type(payload.refresh_token)
        if refresh_payload and refresh_payload.get("sub") == current_user.username:
            if _revoke(db, refresh_payload):
                revoked += 1
    if revoked:
        record(db, AUTH_LOGOUT, actor=current_user, target_type="user",
               target_id=current_user.user_id, request=request)
    db.commit()
    logger.info("User '%s' logged out", current_user.username)
    return LogoutResponse(message="Logged out", revoked_tokens=revoked)


@router.post("/logout-all", response_model=LogoutResponse)
def logout_everywhere(
    request: Request,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LogoutResponse:
    """End every session of this account on every device.

    Works by timestamp rather than by revoking each jti, so it also covers
    tokens this server has never seen. The caller's own token is additionally
    revoked by jti, since a timestamp of whole seconds cannot distinguish it
    from a token minted in the same second.
    """
    _revoke(db, decode_token_unverified_type(token))
    current_user.sessions_revoked_at = revocation_stamp()
    record(db, AUTH_LOGOUT, actor=current_user, target_type="user",
           target_id=current_user.user_id, request=request,
           message="Logged out on every device")
    db.commit()
    return LogoutResponse(message="Logged out on every device", revoked_tokens=0)


# ── Passwords ──────────────────────────────────────────────────────────────

@router.post("/change-password", response_model=TokenResponse)
def change_password(
    request: Request,
    payload: ChangePasswordRequest,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Change your own password. Required before anything else works when the
    account is on a temporary one.

    Ends every other session and returns fresh tokens, so the caller is not
    logged out by its own change.
    """
    if not verify_password(payload.current_password, current_user.password_hash):
        record_auth(
            SessionLocal, AUTH_LOGIN_FAILURE, actor=current_user, actor_label=current_user.username,
            outcome=OUTCOME_FAILURE, message="Password change: current password wrong", request=request,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    if verify_password(payload.new_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The new password must be different")
    if payload.new_password.lower() in (
        current_user.username.lower(), (current_user.email or "").lower()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The password cannot be your username or email",
        )

    _set_password(current_user, payload.new_password)
    # Two mechanisms, because `iat` alone cannot do this. password_changed_at
    # ends every session from an earlier second, and the caller's own token is
    # revoked by jti — which is exact, and is what covers the case where the
    # login and the change land in the same second. A future-dated stamp is
    # not an option here: PyJWT refuses a token whose iat is ahead of the
    # clock, so the replacement pair would be unusable.
    _revoke(db, decode_token_unverified_type(token))
    record(db, AUTH_LOGIN_SUCCESS, actor=current_user, target_type="user",
           target_id=current_user.user_id, request=request, message="Password changed")
    db.commit()
    db.refresh(current_user)
    return _issue_tokens_for(current_user)


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> ForgotPasswordResponse:
    """Step 1 of forgot-password: mint a one-time reset token.

    Always returns the same message, so this cannot be used to discover which
    addresses are registered. The token is random, single-use, expires, and
    only its SHA-256 is stored.

    No mail server is configured in this deployment, so outside production the
    token is also returned, which is what makes the flow usable. That is
    switched off in production and by SHOW_DEV_RESET_TOKEN=false.
    """
    generic_message = "If an account with that email exists, a password reset link has been sent."
    email = payload.email.strip()
    user = db.query(User).filter(func.lower(User.email) == func.lower(email)).first()

    if user is None or not user.active or user.pending_approval:
        return ForgotPasswordResponse(message=generic_message)

    token, expires = generate_reset_token()
    user.reset_token = hash_reset_token(token)
    user.reset_token_expires = expires
    record(db, AUTH_LOGIN_SUCCESS, actor=user, target_type="user", target_id=user.user_id,
           request=request, message="Password reset requested")
    db.commit()

    logger.info(
        "Password reset token issued for '%s' (valid %d minutes)",
        user.username, RESET_TOKEN_EXPIRE_MINUTES,
    )
    show_token = (not IS_PRODUCTION) and _flag("SHOW_DEV_RESET_TOKEN", default=True)
    return ForgotPasswordResponse(
        message=generic_message,
        reset_token=token if show_token else None,
    )


@router.post("/reset-password", response_model=LogoutResponse)
def reset_password(
    request: Request,
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> LogoutResponse:
    """Step 2 of forgot-password: set a new password with the issued token.

    Ends every existing session for that account, since the point of a reset
    is usually that someone else may hold the old credentials.
    """
    invalid = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token"
    )
    user = db.query(User).filter(User.reset_token == hash_reset_token(payload.reset_token)).first()
    if user is None or user.reset_token_expires is None or not user.active or user.pending_approval:
        raise invalid

    expires = user.reset_token_expires
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires:
        raise invalid

    _set_password(user, payload.new_password)
    # Also end sessions opened before the reset, not just ones predating the
    # password change, so a stolen live token cannot survive the reset.
    user.sessions_revoked_at = revocation_stamp()
    record(db, AUTH_LOGIN_SUCCESS, actor=user, target_type="user", target_id=user.user_id,
           request=request, message="Password reset completed")
    db.commit()
    logger.info("Password reset completed for '%s'", user.username)
    return LogoutResponse(message="Password updated. Log in with your new password.", revoked_tokens=0)


@router.post("/seed", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def seed_admin(db: Session = Depends(get_db)) -> User:
    """Create the default admin user if no users exist.

    This is a one-time bootstrap endpoint. Returns 409 if any user
    already exists in the database.
    """
    if not ensure_default_admin(db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Users already exist. Seed is only for initial bootstrap.",
        )

    return db.query(User).filter(func.lower(User.username) == "admin").first()


@router.post(
    "/register-organization",
    response_model=OrganizationRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_organization(
    payload: OrganizationRegistrationRequest,
    db: Session = Depends(get_db),
) -> OrganizationRegistrationResponse:
    """Create a new organization and its first admin user."""
    org_exists = (
        db.query(Organization)
        .filter(
            or_(
                func.lower(Organization.name) == func.lower(payload.organization.name),
                func.lower(Organization.slug) == func.lower(payload.organization.slug),
            )
        )
        .first()
    )
    if org_exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization already exists",
        )

    user_filters = [func.lower(User.username) == func.lower(payload.admin_username)]
    if payload.admin_email:
        user_filters.append(func.lower(User.email) == func.lower(payload.admin_email))
    user_exists = db.query(User).filter(or_(*user_filters)).first()
    if user_exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Admin username or email already exists",
        )

    organization = Organization(**payload.organization.model_dump())
    db.add(organization)
    db.commit()
    db.refresh(organization)

    user = User(
        organization_id=organization.organization_id,
        username=payload.admin_username,
        password_hash=hash_password(payload.admin_password),
        role="admin",
        full_name=payload.admin_full_name,
        email=payload.admin_email,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    membership = OrganizationMembership(
        organization_id=organization.organization_id,
        user_id=user.user_id,
        role="admin",
        status="active",
        is_primary=True,
    )
    db.add(membership)
    db.commit()

    access_token = create_access_token(
        data={"sub": user.username, "role": user.role, "org_id": user.organization_id}
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username, "org_id": user.organization_id}
    )

    return OrganizationRegistrationResponse(
        organization=organization,
        user_id=user.user_id,
        username=user.username,
        role=user.role or "admin",
        access_token=access_token,
        refresh_token=refresh_token,
    )


def _issue_tokens_for(user: User) -> TokenResponse:
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role, "org_id": user.organization_id}
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username, "org_id": user.organization_id}
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        organization_id=user.organization_id,
        must_change_password=bool(user.must_change_password),
    )


@router.post("/google", response_model=TokenResponse)
def google_login(
    payload: GoogleAuthRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate via Google Sign-In.

    Verifies the ID token issued by Google Identity Services against
    GOOGLE_CLIENT_ID, then logs in the matching user (by verified email) or
    provisions a new researcher account in the default organization — an
    admin can promote the role afterward. Requires GOOGLE_CLIENT_ID to be
    configured; see .env.example for setup instructions.
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Sign-In is not configured on this server (GOOGLE_CLIENT_ID is unset).",
        )

    try:
        claims = google_id_token.verify_oauth2_token(
            payload.token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {exc}",
        )

    email = claims.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google account has no email")
    if not claims.get("email_verified", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Google email is not verified")

    user = db.query(User).filter(func.lower(User.email) == func.lower(email)).first()
    if user is None:
        organization = ensure_default_organization(db)
        user = User(
            organization_id=organization.organization_id,
            username=email,
            password_hash=hash_password(secrets.token_urlsafe(32)),
            role=SELF_REGISTER_ROLE,
            full_name=claims.get("name") or email,
            email=email,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        db.add(OrganizationMembership(
            organization_id=organization.organization_id,
            user_id=user.user_id,
            role=SELF_REGISTER_ROLE,
            status="active",
            is_primary=False,
        ))
        db.commit()
        logger.info("Provisioned new user '%s' via Google Sign-In", user.username)

    # Same gates as the password path. Without these, Google sign-in would be
    # a way around a lockout, a pending approval, or a "log out everywhere".
    if user.pending_approval:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=PENDING_MESSAGE)
    if not user.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    if is_account_locked(user.locked_until):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account temporarily locked after too many failed login attempts. Try again later.",
        )

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    logger.info("User '%s' logged in via Google", user.username)
    return _issue_tokens_for(user)


@router.post("/google/mock", response_model=TokenResponse)
def google_login_mock(db: Session = Depends(get_db)) -> TokenResponse:
    """Demo Google Sign-In, used by the frontend only when no real
    GOOGLE_CLIENT_ID/VITE_GOOGLE_CLIENT_ID is configured. Logs into (or
    provisions) a fixed local demo account — no real Google verification
    happens here. Refuses to run when ENVIRONMENT=production so this
    password-less login path can never reach a real deployment.
    """
    if ENVIRONMENT == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Mock Google Sign-In is disabled in production.",
        )

    organization = ensure_default_organization(db)
    user = db.query(User).filter(func.lower(User.username) == "google_demo").first()
    if user is None:
        user = User(
            organization_id=organization.organization_id,
            username="google_demo",
            password_hash=hash_password(secrets.token_urlsafe(32)),
            role=SELF_REGISTER_ROLE,
            full_name="Google Demo User",
            email="google-demo@ovulite.local",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        db.add(OrganizationMembership(
            organization_id=organization.organization_id,
            user_id=user.user_id,
            role=SELF_REGISTER_ROLE,
            status="active",
            is_primary=False,
        ))
        db.commit()

    user.last_login = datetime.now(timezone.utc)
    db.commit()
    logger.info("Demo Google Sign-In used for user '%s'", user.username)
    return _issue_tokens_for(user)

