"""Administrative user management.

Until this existed, adding a user or changing a role meant opening Postgres:
``/auth/register`` is self-service signup, and nothing else touched the users
table. That made the whole RBAC design unusable in practice — roles could be
designed but not assigned.

Every endpoint is admin-only and organization-scoped. Two safety rules are
enforced here rather than left to the caller, because both are easy to trip and
expensive to undo:

* an admin cannot deactivate or demote their own account — that is how an
  organization locks itself out;
* the last remaining active admin cannot be removed or demoted, for the same
  reason one step removed.

Deactivation is used instead of deletion. A user row is referenced by audit
events and by the ``last_login`` history, and deleting it would break the record
of who did what.
"""

import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    ADMIN_ROLES,
    CANONICAL_ROLES,
    ET_WRITE_ROLES,
    LAB_WRITE_ROLES,
    PREDICTION_RUN_ROLES,
    require_role,
)
from app.auth.security import hash_password, revocation_stamp
from app.database import get_db
from app.models.user import User
from app.schemas.admin import (
    AdminPasswordReset,
    AdminUserCreate,
    AdminUserResponse,
    AdminUserUpdate,
    RoleDescriptor,
)
from app.schemas.common import PaginatedResponse
from app.services.audit import record

router = APIRouter()



ROLE_LABELS: dict[str, tuple[str, str]] = {
    "admin": ("Admin", "Full access: user management, system settings, every module, reports and export."),
    "embryologist": ("Embryologist", "Laboratory: OPU, IVF, IVM, embryo grading and lab QC. Can run predictions."),
    "veterinarian": ("Veterinarian", "Recipients, synchronization, protocols, transfers, pregnancy diagnosis and outcomes."),
    "researcher": ("Researcher", "Read-only: dashboard, analytics, model performance, research and literature. No clinical or lab writes."),
}


def _owned(user_id: int, db: Session, actor: User) -> User:
    user = (
        db.query(User)
        .filter(User.user_id == user_id, User.organization_id == actor.organization_id)
        .first()
    )
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _other_active_admins(db: Session, actor: User, excluding: int) -> int:
    return (
        db.query(User)
        .filter(
            User.organization_id == actor.organization_id,
            User.role.in_(ADMIN_ROLES),
            User.active.is_(True),
            User.user_id != excluding,
        )
        .count()
    )


def _guard_last_admin(target: User, db: Session, actor: User, action: str) -> None:
    if target.role in ADMIN_ROLES and target.active and _other_active_admins(db, actor, target.user_id) == 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot {action} the last active administrator — the organization would be locked out.",
        )


def _guard_self(target: User, actor: User, action: str) -> None:
    if target.user_id == actor.user_id:
        raise HTTPException(
            status_code=409,
            detail=f"You cannot {action} your own account. Ask another administrator.",
        )


@router.get("/roles", response_model=list[RoleDescriptor])
def list_roles(_actor: User = Depends(require_role(*ADMIN_ROLES))):
    """The assignable roles and what each one grants.

    Derived from the same tuples the dependencies enforce, so the picker cannot
    drift away from what the API actually allows.
    """
    return [
        RoleDescriptor(
            role=role,
            label=ROLE_LABELS.get(role, (role.title(), ""))[0],
            description=ROLE_LABELS.get(role, (role, ""))[1],
            can_write_lab=role in LAB_WRITE_ROLES,
            can_write_et=role in ET_WRITE_ROLES,
            can_run_predictions=role in PREDICTION_RUN_ROLES,
            is_admin=role in ADMIN_ROLES,
        )
        for role in CANONICAL_ROLES
    ]


@router.get("/users", response_model=PaginatedResponse[AdminUserResponse])
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    include_inactive: bool = Query(True),
    role: str | None = Query(None),
    search: str | None = Query(None, description="Matches username, full name or email"),
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(*ADMIN_ROLES)),
):
    q = db.query(User).filter(User.organization_id == actor.organization_id)
    if not include_inactive:
        q = q.filter(User.active.is_(True))
    if role:
        q = q.filter(User.role == role)
    if search:
        pattern = f"%{search.strip()}%"
        q = q.filter(
            User.username.ilike(pattern)
            | User.full_name.ilike(pattern)
            | User.email.ilike(pattern)
        )
    total = q.count()
    items = q.order_by(User.username).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse(
        items=items, total=total, page=page, page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


@router.get("/users/{user_id}", response_model=AdminUserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(*ADMIN_ROLES)),
):
    return _owned(user_id, db, actor)


@router.post("/users/{user_id}/approve", response_model=AdminUserResponse)
def approve_user(
    user_id: int,
    role: str | None = Query(None, description="Role to grant; defaults to the signup role"),
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(*ADMIN_ROLES)),
):
    """Approve a self-registered account so it can log in.

    Self-signup creates the account with the lowest-privilege role and leaves
    it pending; this is the only path that clears that, and it is admin-only.
    An admin can grant a different role in the same step, which is the point —
    otherwise approving and then promoting would be two audit entries for one
    decision.
    """
    target = _owned(user_id, db, actor)
    if not target.pending_approval:
        raise HTTPException(status_code=409, detail="That account is not waiting for approval.")

    if role is not None:
        if role not in CANONICAL_ROLES:
            raise HTTPException(status_code=422, detail=f"role must be one of {', '.join(CANONICAL_ROLES)}")
        target.role = role

    target.pending_approval = False
    target.active = True
    target.approved_by = actor.username
    target.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(target)
    record(
        db,
        "admin.user.approved",
        actor=actor,
        target_type="user",
        target_id=target.user_id,
        detail={"username": target.username, "role": target.role},
        message=f"Approved {target.username} as {target.role}",
    )
    db.commit()
    db.refresh(target)
    return target


@router.post("/users/{user_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
def reject_user(
    user_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(*ADMIN_ROLES)),
):
    """Refuse a pending signup.

    Deactivated rather than deleted, like every other removal here: the row is
    referenced by the audit trail of its own signup, and a rejected request is
    itself worth being able to look up later.
    """
    target = _owned(user_id, db, actor)
    if not target.pending_approval:
        raise HTTPException(status_code=409, detail="That account is not waiting for approval.")
    target.active = False
    db.commit()
    record(
        db,
        "admin.user.rejected",
        actor=actor,
        target_type="user",
        target_id=target.user_id,
        detail={"username": target.username},
        message=f"Rejected signup for {target.username}",
    )
    db.commit()
    return None


@router.post("/users/{user_id}/unlock", response_model=AdminUserResponse)
def unlock_user(
    user_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(*ADMIN_ROLES)),
):
    """Clear a failed-login lockout without waiting it out."""
    target = _owned(user_id, db, actor)
    target.failed_login_count = 0
    target.locked_until = None
    db.commit()
    record(
        db,
        "admin.user.unlocked",
        actor=actor,
        target_type="user",
        target_id=target.user_id,
        detail={"username": target.username},
        message=f"Cleared the lockout on {target.username}",
    )
    db.commit()
    db.refresh(target)
    return target


@router.post("/users", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(*ADMIN_ROLES)),
):
    # Username uniqueness is global, not per-organization, because it is the
    # login identifier.
    if db.query(User).filter(User.username == payload.username).first() is not None:
        raise HTTPException(status_code=409, detail=f"Username '{payload.username}' is taken.")

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role,
        full_name=payload.full_name,
        email=payload.email,
        active=payload.active,
        organization_id=actor.organization_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}", response_model=AdminUserResponse)
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(*ADMIN_ROLES)),
):
    target = _owned(user_id, db, actor)
    changes = payload.model_dump(exclude_unset=True)

    losing_admin = (
        ("role" in changes and changes["role"] not in ADMIN_ROLES)
        or changes.get("active") is False
    )
    if losing_admin:
        _guard_self(target, actor, "demote or deactivate")
        _guard_last_admin(target, db, actor, "demote or deactivate")

    for field, value in changes.items():
        setattr(target, field, value)
    # Same reason as DELETE: deactivating here must end the live sessions, and
    # a role change must stop tokens that still carry the old role claim.
    if changes.get("active") is False or "role" in changes:
        target.sessions_revoked_at = revocation_stamp()
    db.commit()
    db.refresh(target)
    return target


@router.post("/users/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    user_id: int,
    payload: AdminPasswordReset,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(*ADMIN_ROLES)),
):
    """Set a new password for another user.

    Recorded as its own audit action rather than folded into a general update,
    so a credential change is never invisible inside a name edit.
    """
    target = _owned(user_id, db, actor)
    target.password_hash = hash_password(payload.new_password)
    # An admin-set password is a hand-off credential: the admin knows it, so
    # the user must replace it before anything else answers.
    target.must_change_password = True
    # Ends sessions opened with the old password — otherwise resetting the
    # password of a compromised account left the intruder logged in.
    target.password_changed_at = revocation_stamp()
    target.failed_login_count = 0
    target.locked_until = None
    target.reset_token = None
    target.reset_token_expires = None
    db.commit()
    record(
        db,
        "admin.password.reset",
        actor=actor,
        target_type="user",
        target_id=target.user_id,
        detail={"username": target.username},
        message=f"Password reset for {target.username}",
    )
    db.commit()
    return None


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_role(*ADMIN_ROLES)),
):
    """Deactivate. The row is never deleted — audit history points at it."""
    target = _owned(user_id, db, actor)
    _guard_self(target, actor, "deactivate")
    _guard_last_admin(target, db, actor, "deactivate")
    target.active = False
    # Deactivation has to end the sessions too. Clearing the flag alone left
    # any token the user already held working until it expired, so "remove
    # this person's access" did not remove it for up to 30 minutes.
    target.sessions_revoked_at = revocation_stamp()
    db.commit()
    return None
