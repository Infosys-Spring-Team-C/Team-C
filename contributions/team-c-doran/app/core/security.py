"""JWT authentication and role-based authorization dependencies."""

import os
from dataclasses import dataclass
from typing import Annotated, Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError

_bearer_scheme = HTTPBearer(auto_error=False)
_JWT_ALGORITHM = "HS256"


@dataclass(frozen=True)
class AuthenticatedUser:
    """Identity and role claims accepted from a verified access token."""

    user_id: str
    role: str


def _jwt_secret() -> str:
    """Return the configured signing key, failing closed when absent."""
    secret = os.getenv("JWT_SECRET_KEY")
    if (
        not secret
        or secret == "replace-with-a-long-random-secret"
        or len(secret.encode("utf-8")) < 32
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication requires a configured random JWT secret of at least 32 bytes.",
        )
    return secret


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ],
) -> AuthenticatedUser:
    """Validate a bearer JWT and return its subject and role claims.

    Tokens must be signed with HS256 and contain a non-empty ``sub`` and
    ``role`` claim. PyJWT verifies the signature and expiry when present.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = jwt.decode(
            credentials.credentials,
            _jwt_secret(),
            algorithms=[_JWT_ALGORITHM],
            options={"require": ["exp", "sub", "role"]},
        )
        user_id = claims.get("sub")
        role = claims.get("role")
        if not isinstance(user_id, str) or not user_id.strip():
            raise InvalidTokenError("Token subject must be a non-empty string.")
        if not isinstance(role, str) or not role.strip():
            raise InvalidTokenError("Token role must be a non-empty string.")
    except HTTPException:
        raise
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return AuthenticatedUser(user_id=user_id, role=role.lower())


def require_role(allowed_roles: list[str]) -> Callable[..., AuthenticatedUser]:
    """Build a dependency that permits only users with one of the given roles."""
    normalized_roles = {role.strip().lower() for role in allowed_roles if role.strip()}
    if not normalized_roles:
        raise ValueError("require_role needs at least one non-empty role")

    def role_dependency(
        current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> AuthenticatedUser:
        if current_user.role not in normalized_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role for this operation.",
            )
        return current_user

    return role_dependency
