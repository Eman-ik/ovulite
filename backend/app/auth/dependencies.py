"""FastAPI dependencies for authentication and role-based access control."""

from typing import Callable

from fastapi import Request, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.security import issued_before_password_change, verify_token
from app.database import get_db
from app.models.organization import Organization
from app.models.token_blacklist import RevokedToken
from app.models.user import User
from app.services.audit import set_audit_actor

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# While must_change_password is set, these are the only paths that answer.
# /auth/me so the frontend can see who it is and why it is being redirected,
# change-password so the user can fix it, and the logouts so they can leave.
_PASSWORD_CHANGE_ALLOWED_PATHS = (
    "/auth/me",
    "/auth/change-password",
    "/auth/logout",
    "/auth/logout-all",
)
PASSWORD_CHANGE_REQUIRED = "password_change_required"


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Extract the current user from the JWT bearer token.

    Validates the token, looks up the user in the database,
    and confirms the account is active.
    """
    payload = verify_token(token)
    username: str | None = payload.get("sub")
    token_org_id = payload.get("org_id")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    jti = payload.get("jti")
    if jti is not None and db.query(RevokedToken).filter(RevokedToken.jti == jti).first():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    # A password change or "log out everywhere" ends sessions opened earlier.
    # Checked here rather than at login, because the point is to kill a token
    # someone else is already holding.
    if issued_before_password_change(payload, user.sessions_valid_after):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has ended. Log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )
    if user.pending_approval:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is waiting for an administrator to approve it.",
        )
    # A temporary password gets you exactly far enough to replace it.
    if user.must_change_password and request.url.path not in _PASSWORD_CHANGE_ALLOWED_PATHS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=PASSWORD_CHANGE_REQUIRED,
        )
    if token_org_id is not None and user.organization_id != token_org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token organization mismatch",
        )

    # Bind the actor for this request so the session-level audit listener can
    # attribute any write it observes. Done here rather than in middleware
    # because this is the one place the authenticated user is resolved, so a
    # new router cannot forget it.
    set_audit_actor(
        db,
        user_id=user.user_id,
        username=user.username,
        role=user.role,
        organization_id=user.organization_id,
        request=request,
    )
    return user


def get_current_organization(current_user: User = Depends(get_current_user)) -> Organization:
    """Return the authenticated user's organization."""
    if current_user.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not assigned to an organization",
        )
    organization = current_user.organization
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    return organization


# The four operational roles, plus the two support roles. `role` is a free
# string column on User, so this tuple is the vocabulary rather than a DB
# constraint — it must stay in sync with CANONICAL_ROLES in
# frontend/src/lib/roleRoutes.ts.
#
# "et team" is the legacy string for veterinarian; the imported ET dataset
# uses it, so both are accepted wherever a vet is allowed.
CANONICAL_ROLES = (
    "admin",
    "organization_admin",
    "embryologist",
    "veterinarian",
    "et team",
    "researcher",
    "viewer",
)

# Write/delete role groups for the core clinical CRUD routers. Read access
# (list/get) stays open to any authenticated role; only mutation is
# restricted, split along the lab-side / ET-side line the SRS describes:
# embryologist owns lab data entry, et team/veterinarian own recipient and
# transfer entry. admin and organization_admin can write everywhere.
#
# `researcher` is deliberately absent from both: the role analyses outcomes
# and evaluates models, and must not be able to edit clinical records.
LAB_WRITE_ROLES = ("admin", "organization_admin", "embryologist")
ET_WRITE_ROLES = ("admin", "organization_admin", "et team", "veterinarian")

# Running a prediction is a third thing, and lumping it into ET_WRITE_ROLES
# conflated three different privileges:
#
#   generate a prediction  — asks the model a question about a candidate
#                            transfer. An embryologist deciding whether to
#                            freeze or transfer an embryo has a real use for
#                            it, and it commits nothing clinically.
#   select for a case      — declares which prediction drives this transfer.
#                            A clinical decision, ET-side.
#   record the outcome     — states whether the recipient was pregnant. An
#                            observation only the ET side makes.
#
# So only the first opens to the lab. The other two stay on ET_WRITE_ROLES.
PREDICTION_RUN_ROLES = (
    "admin",
    "organization_admin",
    "et team",
    "veterinarian",
    "embryologist",
)


def require_role(*allowed_roles: str) -> Callable:
    """Return a dependency that restricts access to users with specific roles.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role("admin"))])
    """

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' not authorized. Required: {', '.join(allowed_roles)}",
            )
        return current_user

    return role_checker
