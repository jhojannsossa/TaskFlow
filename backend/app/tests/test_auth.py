import uuid

import pytest

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.database.connection import engine, get_db
from backend.app.models.user import User
from backend.app.core.security import hash_password


@pytest.fixture
def db_session():
    """Sesión de pruebas con rollback automático."""

    connection = engine.connect()
    transaction = connection.begin()

    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session):
    """Cliente FastAPI con la sesión de pruebas."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def test_user(db_session):
    """Crea un usuario de prueba."""

    user = User(
        name="Usuario Autenticación",
        email=f"auth-{uuid.uuid4().hex}@example.com",
        password_hash=hash_password("ClaveSegura123!"),
        is_active=True,
    )

    db_session.add(user)
    db_session.flush()

    return user


def test_register_user(client):
    """Debe registrar un usuario correctamente."""

    response = client.post(
        "/api/auth/register",
        json={
            "name": "Nuevo Usuario",
            "email": f"nuevo-{uuid.uuid4().hex}@example.com",
            "password": "ClaveSegura123!",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Nuevo Usuario"
    assert data["is_active"] is True
    assert "password" not in data
    assert "password_hash" not in data


def test_register_duplicate_email(client, test_user):
    """Debe rechazar un correo duplicado."""

    response = client.post(
        "/api/auth/register",
        json={
            "name": "Usuario Duplicado",
            "email": test_user.email,
            "password": "OtraClave123!",
        },
    )

    assert response.status_code == 409


def test_login_success(client, test_user):
    """Debe permitir iniciar sesión."""

    response = client.post(
        "/api/auth/login",
        json={
            "email": test_user.email,
            "password": "ClaveSegura123!",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, test_user):
    """Debe rechazar contraseñas incorrectas."""

    response = client.post(
        "/api/auth/login",
        json={
            "email": test_user.email,
            "password": "ClaveIncorrecta123",
        },
    )

    assert response.status_code == 401


def test_me_without_token(client):
    """Debe rechazar solicitudes sin token."""

    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_me_with_valid_token(client, test_user):
    """Debe devolver el perfil autenticado."""

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": test_user.email,
            "password": "ClaveSegura123!",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.get(
        "/api/auth/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200
    assert response.json()["id"] == test_user.id
    assert response.json()["email"] == test_user.email


def test_me_with_invalid_token(client):
    """Debe rechazar un token inválido."""

    response = client.get(
        "/api/auth/me",
        headers={
            "Authorization": "Bearer token-invalido",
        },
    )

    assert response.status_code == 401

from datetime import datetime, timedelta, timezone

import jwt

from backend.app.core.config import settings


def test_login_inactive_user(client, test_user, db_session):
    """Un usuario desactivado no puede iniciar sesión."""

    test_user.is_active = False
    db_session.flush()

    response = client.post(
        "/api/auth/login",
        json={
            "email": test_user.email,
            "password": "ClaveSegura123!",
        },
    )

    assert response.status_code == 403


def test_me_inactive_user(client, test_user, db_session):
    """Un usuario desactivado no puede acceder a su perfil."""

    login_response = client.post(
        "/api/auth/login",
        json={
            "email": test_user.email,
            "password": "ClaveSegura123!",
        },
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    test_user.is_active = False
    db_session.flush()

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_me_with_expired_token(client, test_user):
    """Un token caducado debe ser rechazado."""

    expired_at = datetime.now(timezone.utc) - timedelta(minutes=5)

    token = jwt.encode(
        {
            "sub": str(test_user.id),
            "iat": expired_at - timedelta(minutes=60),
            "exp": expired_at,
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
