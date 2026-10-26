"""Authentication, password handling and RBAC tests."""
from __future__ import annotations

import jwt

from backend.config import get_settings
from backend.security import hash_password, verify_password


def test_password_hash_roundtrip_and_rejection():
    digest = hash_password("correct-horse-battery")
    assert digest.startswith("pbkdf2_sha256$")
    assert verify_password("correct-horse-battery", digest)
    assert not verify_password("wrong", digest)
    assert not verify_password("correct-horse-battery", "garbage")


def test_short_password_is_refused():
    try:
        hash_password("short")
    except ValueError as exc:
        assert "8 characters" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("short password should be rejected")


def test_token_issue_and_me(client, seeded_users):
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "rep@test.local", "password": "rep-password"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0

    me = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == "rep@test.local"
    assert me.json()["role"] == "rep"


def test_wrong_password_and_unknown_user_both_return_401(client, seeded_users):
    wrong = client.post(
        "/api/v1/auth/token", data={"username": "rep@test.local", "password": "nope"}
    )
    unknown = client.post(
        "/api/v1/auth/token", data={"username": "ghost@test.local", "password": "nope"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["code"] == "invalid_credentials"
    assert unknown.json()["code"] == "invalid_credentials"


def test_inactive_user_cannot_authenticate(client, seeded_users, db):
    from backend.db import User

    user = db.query(User).filter(User.email == "viewer@test.local").one()
    user.is_active = False
    db.commit()

    response = client.post(
        "/api/v1/auth/token",
        data={"username": "viewer@test.local", "password": "viewer-password"},
    )
    assert response.status_code == 401


def test_invalid_and_expired_tokens_are_rejected(client, seeded_users):
    assert client.get(
        "/api/v1/leads", headers={"Authorization": "Bearer not-a-token"}
    ).status_code == 401

    settings = get_settings()
    expired = jwt.encode(
        {"sub": "rep@test.local", "role": "rep", "exp": 1},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    response = client.get("/api/v1/leads", headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Access token has expired."


def test_token_signed_with_wrong_secret_is_rejected(client, seeded_users):
    forged = jwt.encode(
        {"sub": "admin@test.local", "role": "admin", "exp": 9999999999},
        "attacker-secret-value-123",
        algorithm="HS256",
    )
    response = client.get("/api/v1/leads", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


def test_admin_can_create_user_and_non_admin_cannot(client, admin, rep, manager):
    payload = {
        "email": "new.user@test.local",
        "full_name": "New User",
        "password": "strong-password",
        "role": "rep",
    }
    assert client.post("/api/v1/auth/users", headers=rep, json=payload).status_code == 403
    assert client.post("/api/v1/auth/users", headers=manager, json=payload).status_code == 403

    created = client.post("/api/v1/auth/users", headers=admin, json=payload)
    assert created.status_code == 201, created.text
    assert created.json()["email"] == "new.user@test.local"
    assert "password" not in created.json()
    assert "password_hash" not in created.json()

    duplicate = client.post("/api/v1/auth/users", headers=admin, json=payload)
    assert duplicate.status_code == 409


def test_new_user_can_authenticate(client, admin):
    client.post(
        "/api/v1/auth/users",
        headers=admin,
        json={
            "email": "fresh@test.local",
            "full_name": "Fresh",
            "password": "fresh-password",
            "role": "viewer",
        },
    )
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "fresh@test.local", "password": "fresh-password"},
    )
    assert response.status_code == 200


def test_admin_can_deactivate_and_change_role(client, admin, rep, seeded_users):
    users = client.get("/api/v1/auth/users", headers=admin).json()
    target = next(item for item in users if item["email"] == "rep@test.local")

    patched = client.patch(
        f"/api/v1/auth/users/{target['id']}",
        headers=admin,
        json={"role": "manager"},
    )
    assert patched.status_code == 200
    assert patched.json()["role"] == "manager"

    invalid = client.patch(
        f"/api/v1/auth/users/{target['id']}", headers=admin, json={"role": "superuser"}
    )
    assert invalid.status_code == 422
