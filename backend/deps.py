"""FastAPI dependencies: database session, authenticated principal, RBAC."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.db import User, get_db
from backend.errors import ApiError
from backend.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


@dataclass(frozen=True)
class Principal:
    id: int | None
    email: str
    role: str

    @property
    def is_anonymous(self) -> bool:
        return self.id is None


def _unauthenticated(message: str = "Not authenticated.") -> ApiError:
    return ApiError(401, "not_authenticated", message)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Principal:
    settings = get_settings()

    if not settings.auth_enabled:
        # Explicit, documented development switch.  Never enabled in the
        # provided Docker configuration.
        return Principal(id=None, email="anonymous@local", role="admin")

    if not token:
        raise _unauthenticated()

    try:
        payload = decode_access_token(token, settings)
    except jwt.ExpiredSignatureError as exc:
        raise _unauthenticated("Access token has expired.") from exc
    except jwt.PyJWTError as exc:
        raise _unauthenticated("Access token is invalid.") from exc

    subject = payload.get("sub")
    if not subject:
        raise _unauthenticated("Access token is missing a subject.")

    user = db.scalar(select(User).where(User.email == subject))
    if user is None or not user.is_active:
        raise _unauthenticated("User is inactive or no longer exists.")

    return Principal(id=user.id, email=user.email, role=user.role)


def require_roles(*roles: str):
    """Dependency factory enforcing that the caller holds one of ``roles``."""
    allowed = set(roles)

    def _dependency(principal: Principal = Depends(get_current_user)) -> Principal:
        if principal.role not in allowed:
            raise ApiError(
                403,
                "forbidden",
                f"This action requires one of the roles: {', '.join(sorted(allowed))}.",
            )
        return principal

    return _dependency


#: Roles permitted to mutate business data.
WRITE_ROLES: Iterable[str] = ("admin", "manager", "rep")
#: Roles permitted to delete leads and manage users.
ADMIN_ROLES: Iterable[str] = ("admin", "manager")

require_writer = require_roles(*WRITE_ROLES)
require_manager = require_roles(*ADMIN_ROLES)
require_admin = require_roles("admin")
