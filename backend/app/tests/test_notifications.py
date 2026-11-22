import uuid

import pytest

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.database.connection import engine, get_db
from backend.app.core.security import create_access_token
from backend.app.models.user import User
from backend.app.models.notification import Notification
from backend.app.models.notification_preference import NotificationPreference
from sqlalchemy import select, func

from backend.app.models.task_list import TaskList
from backend.app.models.list_member import ListMember

@pytest.fixture
def db_session():
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
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def users(db_session):
    result = []

    for name in ["Usuario principal", "Otro usuario"]:
        user = User(
            name=name,
            email=f"{uuid.uuid4().hex}@example.com",
            password_hash="hash_de_prueba",
            is_active=True,
        )
        db_session.add(user)
        result.append(user)

    db_session.flush()
    return result


@pytest.fixture
def notifications(db_session, users):
    first = Notification(
        user_id=users[0].id,
        type="assignment",
        message="Te han asignado una tarea.",
    )

    second = Notification(
        user_id=users[0].id,
        type="status_change",
        message="Una tarea ha cambiado de estado.",
    )

    other = Notification(
        user_id=users[1].id,
        type="assignment",
        message="Notificación de otro usuario.",
    )

    db_session.add_all([first, second, other])
    db_session.flush()

    return first, second, other


def auth_headers(user):
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


def test_notifications_require_authentication(client):
    response = client.get("/api/notifications")

    assert response.status_code == 401


def test_user_can_list_own_notifications(
    client,
    users,
    notifications,
):
    response = client.get(
        "/api/notifications",
        headers=auth_headers(users[0]),
    )

    assert response.status_code == 200

    returned_ids = {
        item["id"]
        for item in response.json()
    }

    assert notifications[0].id in returned_ids
    assert notifications[1].id in returned_ids
    assert notifications[2].id not in returned_ids


def test_user_can_mark_notification_as_read(
    client,
    users,
    notifications,
):
    notification_id = notifications[0].id

    response = client.patch(
        f"/api/notifications/{notification_id}/read",
        headers=auth_headers(users[0]),
    )

    assert response.status_code == 200
    assert response.json()["is_read"] is True


def test_user_cannot_mark_another_users_notification(
    client,
    users,
    notifications,
):
    notification_id = notifications[2].id

    response = client.patch(
        f"/api/notifications/{notification_id}/read",
        headers=auth_headers(users[0]),
    )

    assert response.status_code == 404


def test_user_can_mark_all_notifications_as_read(
    client,
    db_session,
    users,
    notifications,
):
    response = client.patch(
        "/api/notifications/read-all",
        headers=auth_headers(users[0]),
    )

    assert response.status_code == 200
    assert response.json()["updated_count"] == 2

    db_session.expire_all()

    assert db_session.get(
        Notification,
        notifications[0].id,
    ).is_read is True

    assert db_session.get(
        Notification,
        notifications[1].id,
    ).is_read is True

    assert db_session.get(
        Notification,
        notifications[2].id,
    ).is_read is False


def test_user_can_get_default_preferences(
    client,
    users,
):
    response = client.get(
        "/api/notifications/preferences",
        headers=auth_headers(users[0]),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["user_id"] == users[0].id
    assert data["due_soon"] is True
    assert data["overdue"] is True
    assert data["status_changes"] is True
    assert data["assignments"] is True
    assert data["shared_list_updates"] is True


def test_user_can_update_preferences(
    client,
    users,
):
    response = client.patch(
        "/api/notifications/preferences",
        headers=auth_headers(users[0]),
        json={
            "assignments": False,
            "due_soon": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["assignments"] is False
    assert response.json()["due_soon"] is False
    assert response.json()["overdue"] is True


def test_user_preferences_are_independent(
    client,
    users,
):
    client.patch(
        "/api/notifications/preferences",
        headers=auth_headers(users[0]),
        json={"assignments": False},
    )

    response = client.get(
        "/api/notifications/preferences",
        headers=auth_headers(users[1]),
    )

    assert response.status_code == 200
    assert response.json()["assignments"] is True


def test_invalid_preference_value_is_rejected(
    client,
    users,
):
    response = client.patch(
        "/api/notifications/preferences",
        headers=auth_headers(users[0]),
        json={"assignments": "valor_invalido"},
    )

    assert response.status_code == 422


def test_mark_nonexistent_notification_returns_404(
    client,
    users,
):
    response = client.patch(
        "/api/notifications/999999999/read",
        headers=auth_headers(users[0]),
    )

    assert response.status_code == 404

def test_task_assignment_creates_notification(
    client,
    db_session,
    users,
):
    """Asignar una tarea a otro usuario genera una notificación."""

    owner = users[0]
    collaborator = users[1]

    # Crear una lista compartida.
    task_list = TaskList(
        owner_id=owner.id,
        name="Lista para probar notificaciones",
        visibility="shared",
    )

    db_session.add(task_list)
    db_session.flush()

    # Añadir al segundo usuario como colaborador.
    membership = ListMember(
        list_id=task_list.id,
        user_id=collaborator.id,
        role="editor",
    )

    db_session.add(membership)
    db_session.flush()

    # Crear una tarea asignada al colaborador.
    response = client.post(
        "/api/tasks",
        headers=auth_headers(owner),
        json={
            "list_id": task_list.id,
            "title": "Preparar documentación",
            "assigned_to": collaborator.id,
        },
    )

    assert response.status_code == 201

    task_id = response.json()["id"]

    # Buscar la notificación creada automáticamente.
    notification = db_session.scalar(
        select(Notification).where(
            Notification.user_id == collaborator.id,
            Notification.task_id == task_id,
            Notification.type == "assignment",
        )
    )

    assert notification is not None
    assert notification.is_read is False
    assert "Preparar documentación" in notification.message

def test_task_status_change_creates_notification(
    client,
    db_session,
    users,
):
    """Cambiar el estado notifica al responsable de la tarea."""

    owner = users[0]
    collaborator = users[1]

    # Crear una lista compartida.
    task_list = TaskList(
        owner_id=owner.id,
        name="Lista para cambios de estado",
        visibility="shared",
    )
    db_session.add(task_list)
    db_session.flush()

    # Añadir al colaborador.
    membership = ListMember(
        list_id=task_list.id,
        user_id=collaborator.id,
        role="editor",
    )
    db_session.add(membership)
    db_session.flush()

    # Crear tarea asignada al colaborador.
    created = client.post(
        "/api/tasks",
        headers=auth_headers(owner),
        json={
            "list_id": task_list.id,
            "title": "Revisar documentación",
            "assigned_to": collaborator.id,
        },
    )

    assert created.status_code == 201
    task_id = created.json()["id"]

    # Cambiar el estado de la tarea.
    updated = client.patch(
        f"/api/tasks/{task_id}",
        headers=auth_headers(owner),
        json={"status": "in_progress"},
    )

    assert updated.status_code == 200
    assert updated.json()["status"] == "in_progress"

    # Comprobar que se generó la notificación.
    notification = db_session.scalar(
        select(Notification).where(
            Notification.user_id == collaborator.id,
            Notification.task_id == task_id,
            Notification.type == "status_change",
        )
    )

    assert notification is not None
    assert notification.is_read is False
    assert "Revisar documentación" in notification.message

def test_disabled_assignment_preference_prevents_notification(
    client,
    db_session,
    users,
):
    """No se notifica una asignación si el usuario la desactivó."""

    owner = users[0]
    collaborator = users[1]

    task_list = TaskList(
        owner_id=owner.id,
        name="Lista para probar preferencias",
        visibility="shared",
    )
    db_session.add(task_list)
    db_session.flush()

    membership = ListMember(
        list_id=task_list.id,
        user_id=collaborator.id,
        role="editor",
    )
    db_session.add(membership)
    db_session.flush()

    # El colaborador desactiva las notificaciones de asignación.
    preference_response = client.patch(
        "/api/notifications/preferences",
        headers=auth_headers(collaborator),
        json={"assignments": False},
    )

    assert preference_response.status_code == 200
    assert preference_response.json()["assignments"] is False

    # El propietario le asigna una tarea.
    created = client.post(
        "/api/tasks",
        headers=auth_headers(owner),
        json={
            "list_id": task_list.id,
            "title": "Tarea sin aviso",
            "assigned_to": collaborator.id,
        },
    )

    assert created.status_code == 201

    task_id = created.json()["id"]

    # No debe existir una notificación de asignación.
    notification = db_session.scalar(
        select(Notification).where(
            Notification.user_id == collaborator.id,
            Notification.task_id == task_id,
            Notification.type == "assignment",
        )
    )

    assert notification is None