import uuid

import pytest

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.database.connection import engine, get_db
from backend.app.core.security import create_access_token
from backend.app.models.user import User
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

    for name in ["Propietario", "Editor", "Visualizador", "Ajeno"]:
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
def task_list(db_session, users):
    owner = users[0]

    new_list = TaskList(
        owner_id=owner.id,
        name="Lista de pruebas",
        visibility="shared",
    )

    db_session.add(new_list)
    db_session.flush()

    db_session.add_all([
        ListMember(
            list_id=new_list.id,
            user_id=users[1].id,
            role="editor",
        ),
        ListMember(
            list_id=new_list.id,
            user_id=users[2].id,
            role="viewer",
        ),
    ])

    db_session.flush()

    return new_list


def auth_headers(user):
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


def test_create_task(client, users, task_list):
    response = client.post(
        "/api/tasks",
        headers=auth_headers(users[0]),
        json={
            "list_id": task_list.id,
            "title": "Crear primera tarea",
            "priority": "high",
        },
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Crear primera tarea"
    assert response.json()["status"] == "todo"


def test_list_tasks(client, users, task_list):
    client.post(
        "/api/tasks",
        headers=auth_headers(users[0]),
        json={
            "list_id": task_list.id,
            "title": "Tarea visible",
        },
    )

    response = client.get(
        "/api/tasks",
        headers=auth_headers(users[0]),
    )

    assert response.status_code == 200
    assert any(
        task["title"] == "Tarea visible"
        for task in response.json()
    )


def test_update_task(client, users, task_list):
    created = client.post(
        "/api/tasks",
        headers=auth_headers(users[0]),
        json={
            "list_id": task_list.id,
            "title": "Tarea pendiente",
        },
    )

    assert created.status_code == 201
    task_id = created.json()["id"]

    response = client.patch(
        f"/api/tasks/{task_id}",
        headers=auth_headers(users[0]),
        json={"status": "done"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "done"
    assert response.json()["completed_at"] is not None


def test_delete_task(client, users, task_list):
    created = client.post(
        "/api/tasks",
        headers=auth_headers(users[0]),
        json={
            "list_id": task_list.id,
            "title": "Tarea eliminable",
        },
    )

    assert created.status_code == 201
    task_id = created.json()["id"]

    response = client.delete(
        f"/api/tasks/{task_id}",
        headers=auth_headers(users[0]),
    )

    assert response.status_code == 204

    response = client.get(
        f"/api/tasks/{task_id}",
        headers=auth_headers(users[0]),
    )

    assert response.status_code == 404


def test_viewer_cannot_create_task(client, users, task_list):
    response = client.post(
        "/api/tasks",
        headers=auth_headers(users[2]),
        json={
            "list_id": task_list.id,
            "title": "Tarea no autorizada",
        },
    )

    assert response.status_code == 403


def test_editor_can_create_task(client, users, task_list):
    response = client.post(
        "/api/tasks",
        headers=auth_headers(users[1]),
        json={
            "list_id": task_list.id,
            "title": "Tarea del editor",
        },
    )

    assert response.status_code == 201


def test_outsider_cannot_create_task(client, users, task_list):
    response = client.post(
        "/api/tasks",
        headers=auth_headers(users[3]),
        json={
            "list_id": task_list.id,
            "title": "Tarea ajena",
        },
    )

    assert response.status_code == 404


def test_tasks_require_authentication(client):
    response = client.get("/api/tasks")

    assert response.status_code == 401

def test_read_task_by_id(client, users, task_list):
    """El propietario puede consultar una tarea por ID."""

    created = client.post(
        "/api/tasks",
        headers=auth_headers(users[0]),
        json={
            "list_id": task_list.id,
            "title": "Consultar tarea",
        },
    )

    assert created.status_code == 201
    task_id = created.json()["id"]

    response = client.get(
        f"/api/tasks/{task_id}",
        headers=auth_headers(users[0]),
    )

    assert response.status_code == 200
    assert response.json()["id"] == task_id


def test_outsider_cannot_read_task(client, users, task_list):
    """Un usuario ajeno no puede consultar tareas privadas."""

    created = client.post(
        "/api/tasks",
        headers=auth_headers(users[0]),
        json={
            "list_id": task_list.id,
            "title": "Tarea protegida",
        },
    )

    assert created.status_code == 201
    task_id = created.json()["id"]

    response = client.get(
        f"/api/tasks/{task_id}",
        headers=auth_headers(users[3]),
    )

    assert response.status_code == 404


def test_viewer_cannot_update_task(client, users, task_list):
    """Un visualizador no puede modificar tareas."""

    created = client.post(
        "/api/tasks",
        headers=auth_headers(users[0]),
        json={
            "list_id": task_list.id,
            "title": "Tarea del propietario",
        },
    )

    assert created.status_code == 201
    task_id = created.json()["id"]

    response = client.patch(
        f"/api/tasks/{task_id}",
        headers=auth_headers(users[2]),
        json={"title": "Modificación no permitida"},
    )

    assert response.status_code == 403


def test_viewer_cannot_delete_task(client, users, task_list):
    """Un visualizador no puede eliminar tareas."""

    created = client.post(
        "/api/tasks",
        headers=auth_headers(users[0]),
        json={
            "list_id": task_list.id,
            "title": "Tarea protegida",
        },
    )

    assert created.status_code == 201
    task_id = created.json()["id"]

    response = client.delete(
        f"/api/tasks/{task_id}",
        headers=auth_headers(users[2]),
    )

    assert response.status_code == 403


def test_invalid_task_status(client, users, task_list):
    """La API rechaza estados de tarea inválidos."""

    response = client.post(
        "/api/tasks",
        headers=auth_headers(users[0]),
        json={
            "list_id": task_list.id,
            "title": "Tarea con estado inválido",
            "status": "cancelled",
        },
    )

    assert response.status_code == 422


def test_completed_at_is_cleared(client, users, task_list):
    """Al reabrir una tarea se elimina su fecha de finalización."""

    created = client.post(
        "/api/tasks",
        headers=auth_headers(users[0]),
        json={
            "list_id": task_list.id,
            "title": "Tarea para reabrir",
            "status": "done",
        },
    )

    assert created.status_code == 201
    task_id = created.json()["id"]
    assert created.json()["completed_at"] is not None

    response = client.patch(
        f"/api/tasks/{task_id}",
        headers=auth_headers(users[0]),
        json={"status": "in_progress"},
    )

    assert response.status_code == 200
    assert response.json()["completed_at"] is None

def test_outsider_cannot_list_private_tasks(
    client,
    users,
    task_list,
):
    """Un usuario ajeno no debe ver tareas de otra lista."""

    created = client.post(
        "/api/tasks",
        headers=auth_headers(users[0]),
        json={
            "list_id": task_list.id,
            "title": "Tarea confidencial",
        },
    )

    assert created.status_code == 201

    private_task_id = created.json()["id"]

    response = client.get(
        "/api/tasks",
        headers=auth_headers(users[3]),
    )

    assert response.status_code == 200

    visible_ids = {
        task["id"]
        for task in response.json()
    }

    assert private_task_id not in visible_ids

def test_member_cannot_read_task_in_private_list(
    client,
    db_session,
    users,
    task_list,
):
    """Un colaborador no puede consultar tareas de una lista privada."""

    created = client.post(
        "/api/tasks",
        headers=auth_headers(users[0]),
        json={
            "list_id": task_list.id,
            "title": "Tarea privada",
        },
    )

    assert created.status_code == 201
    task_id = created.json()["id"]

    task_list.visibility = "private"
    db_session.flush()

    response = client.get(
        f"/api/tasks/{task_id}",
        headers=auth_headers(users[1]),
    )

    assert response.status_code == 404


def test_member_cannot_list_tasks_in_private_list(
    client,
    db_session,
    users,
    task_list,
):
    """Las tareas privadas no aparecen en el listado del colaborador."""

    created = client.post(
        "/api/tasks",
        headers=auth_headers(users[0]),
        json={
            "list_id": task_list.id,
            "title": "Tarea oculta",
        },
    )

    assert created.status_code == 201
    task_id = created.json()["id"]

    task_list.visibility = "private"
    db_session.flush()

    response = client.get(
        "/api/tasks",
        headers=auth_headers(users[1]),
    )

    assert response.status_code == 200

    visible_ids = {
        task["id"]
        for task in response.json()
    }

    assert task_id not in visible_ids


def test_editor_cannot_create_task_in_private_list(
    client,
    db_session,
    users,
    task_list,
):
    """Un editor pierde permiso de creación cuando la lista es privada."""

    task_list.visibility = "private"
    db_session.flush()

    response = client.post(
        "/api/tasks",
        headers=auth_headers(users[1]),
        json={
            "list_id": task_list.id,
            "title": "Tarea no permitida",
        },
    )

    assert response.status_code == 404


def test_editor_cannot_update_task_in_private_list(
    client,
    db_session,
    users,
    task_list,
):
    """Un editor no puede modificar tareas de una lista privada."""

    created = client.post(
        "/api/tasks",
        headers=auth_headers(users[0]),
        json={
            "list_id": task_list.id,
            "title": "Tarea protegida",
        },
    )

    assert created.status_code == 201
    task_id = created.json()["id"]

    task_list.visibility = "private"
    db_session.flush()

    response = client.patch(
        f"/api/tasks/{task_id}",
        headers=auth_headers(users[1]),
        json={"title": "Cambio no autorizado"},
    )

    assert response.status_code == 404


def test_editor_cannot_delete_task_in_private_list(
    client,
    db_session,
    users,
    task_list,
):
    """Un editor no puede eliminar tareas de una lista privada."""

    created = client.post(
        "/api/tasks",
        headers=auth_headers(users[0]),
        json={
            "list_id": task_list.id,
            "title": "Tarea que debe conservarse",
        },
    )

    assert created.status_code == 201
    task_id = created.json()["id"]

    task_list.visibility = "private"
    db_session.flush()

    response = client.delete(
        f"/api/tasks/{task_id}",
        headers=auth_headers(users[1]),
    )

    assert response.status_code == 404

    owner_response = client.get(
        f"/api/tasks/{task_id}",
        headers=auth_headers(users[0]),
    )

    assert owner_response.status_code == 200