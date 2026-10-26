"""Authentication and user administration."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.db import ROLES, User, get_db
from backend.deps import Principal, get_current_user, require_admin
from backend.errors import ApiError
from backend.schemas import TokenResponse, UserCreate, UserRead
from backend.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

#: Verified against when the account does not exist, so response timing does not
#: reveal whether an e-mail is registered.
_DUMMY_HASH = (
    "pbkdf2_sha256$260000$"
    "00000000000000000000000000000000$"
    "0000000000000000000000000000000000000000000000000000000000000000"
)


@router.post("/token", response_model=TokenResponse)
def issue_token(
    form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> TokenResponse:
    settings = get_settings()
    if not settings.auth_enabled:
        raise ApiError(
            400,
            "auth_disabled",
            "Authentication is disabled in this environment (AUTH_ENABLED=false).",
        )

    email = form.username.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    stored = user.password_hash if user else _DUMMY_HASH
    password_ok = verify_password(form.password, stored)

    if user is None or not password_ok or not user.is_active:
        raise ApiError(401, "invalid_credentials", "Incorrect email or password.")

    token, expires_in = create_access_token(user.email, user.role, settings)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=UserRead)
def read_me(
    principal: Principal = Depends(get_current_user), db: Session = Depends(get_db)
) -> UserRead:
    if principal.id is None:
        raise ApiError(
            400,
            "auth_disabled",
            "Authentication is disabled; no user profile is associated with this request.",
        )
    user = db.get(User, principal.id)
    if user is None:  # pragma: no cover - defensive
        raise ApiError(404, "user_not_found", "User not found.")
    return UserRead.model_validate(user)


@router.get("/users", response_model=list[UserRead])
def list_users(
    _: Principal = Depends(require_admin), db: Session = Depends(get_db)
) -> list[UserRead]:
    users = db.scalars(select(User).order_by(User.id)).all()
    return [UserRead.model_validate(user) for user in users]


@router.post("/users", response_model=UserRead, status_code=201)
def create_user(
    body: UserCreate,
    _: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserRead:
    if body.role not in ROLES:
        raise ApiError(422, "invalid_role", f"Role must be one of: {', '.join(ROLES)}.")
    existing = db.scalar(select(User).where(User.email == body.email))
    if existing is not None:
        raise ApiError(409, "user_exists", "A user with this email already exists.")
    user = User(
        email=body.email,
        full_name=body.full_name,
        password_hash=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    body: dict,
    _: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserRead:
    user = db.get(User, user_id)
    if user is None:
        raise ApiError(404, "user_not_found", f"User {user_id} was not found.")

    if "role" in body:
        role = str(body["role"])
        if role not in ROLES:
            raise ApiError(422, "invalid_role", f"Role must be one of: {', '.join(ROLES)}.")
        user.role = role
    if "is_active" in body:
        user.is_active = bool(body["is_active"])
    if "full_name" in body:
        user.full_name = str(body["full_name"])[:200]

    db.commit()
    db.refresh(user)
    return UserRead.model_validate(user)
