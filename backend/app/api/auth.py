"""Authentication API endpoints — login, register, seed, me."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)
from app.database import get_db
from app.models.user import User
from app.schemas.auth import TokenResponse, RefreshTokenRequest
from app.schemas.user import UserCreate, UserResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def ensure_default_admin(db: Session) -> bool:
    """Create the default admin user if the database is empty.

    Returns True when a new admin user was created, False otherwise.
    """
    user_count = db.query(User).count()
    if user_count > 0:
        return False

    admin = User(
        username="admin",
        password_hash=hash_password("ovulite2026"),
        role="admin",
        full_name="System Administrator",
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    logger.info("Default admin user seeded")
    return True


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate a user and return a JWT access token.

    Accepts OAuth2-compatible form data (username + password fields).
    """
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
    if user is None or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Update last_login timestamp
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    access_token = create_access_token(
        data={"sub": user.username, "role": user.role}
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username}
    )
    logger.info("User '%s' logged in successfully", user.username)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_access_token(
    payload: RefreshTokenRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Exchange a valid refresh token for a new access token.
    
    Accepts refresh_token as JSON body field.
    Returns new access_token and the same refresh_token.
    """
    try:
        # Verify refresh token (must be type="refresh")
        token_payload = verify_token(payload.refresh_token, token_type="refresh")
        username = token_payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        
        # Verify user still exists and is active
        user = db.query(User).filter(func.lower(User.username) == func.lower(username)).first()
        if user is None or not user.active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )
        
        # Create new access token
        new_access_token = create_access_token(
            data={"sub": user.username, "role": user.role}
        )
        
        logger.info("Refreshed access token for user '%s'", user.username)
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=payload.refresh_token,  # Return same refresh token
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Token refresh failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not refresh token",
        )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: UserCreate,
    db: Session = Depends(get_db),
) -> User:
    """Register a new user account.

    Open for initial setup; should be admin-only in production.
    """
    existing = db.query(User).filter(func.lower(User.username) == func.lower(payload.username)).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{payload.username}' already exists",
        )

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role,
        full_name=payload.full_name,
        email=payload.email,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("User '%s' registered with role '%s'", user.username, user.role)
    return user


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Return the currently authenticated user's profile."""
    return current_user


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

