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
from sqlalchemy import select


@pytest.fixture
def db_session():
    """Crea una sesión de prueba y revierte sus cambios."""

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
    """Configura el cliente HTTP de pruebas."""

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
    """Crea tres usuarios de prueba."""

    result = []

    for name in ["Propietario", "Colaborador", "Ajeno"]:
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
    """Crea una lista perteneciente al primer usuario."""

    new_list = TaskList(
        owner_id=users[0].id,
        name="Lista de pruebas",
        description="Lista para comprobar permisos",
        visibility="shared",
    )

    db_session.add(new_list)
    db_session.flush()

    return new_list


def auth_headers(user):
    """Genera el encabezado de autenticación JWT."""

    token = create_access_token(user.id)

    return {
        "Authorization": f"Bearer {token}"
    }


def test_create_list(client, users):
    """El propietario puede crear una lista."""

    response = client.post(
        "/api/lists",
        headers=auth_headers(users[0]),
        json={
            "name": "Mi primera lista",
            "description": "Tareas del bootcamp",
            "visibility": "private",
        },
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Mi primera lista"
    assert response.json()["owner_id"] == users[0].id
    assert response.json()["visibility"] == "private"


def test_create_list_requires_authentication(client):
    """No se pueden crear listas sin autenticación."""

    response = client.post(
        "/api/lists",
        json={"name": "Lista sin autorización"},
    )

    assert response.status_code == 401


def test_list_own_lists(client, users, task_list):
    """El propietario puede consultar sus listas."""

    response = client.get(
        "/api/lists",
        headers=auth_headers(users[0]),
    )

    assert response.status_code == 200

    list_ids = {
        item["id"]
        for item in response.json()
    }

    assert task_list.id in list_ids


def test_get_list_by_id(client, users, task_list):
    """El propietario puede consultar una lista por ID."""

    response = client.get(
        f"/api/lists/{task_list.id}",
        headers=auth_headers(users[0]),
    )

    assert response.status_code == 200
    assert response.json()["id"] == task_list.id


def test_outsider_cannot_read_list(client, users, task_list):
    """Un usuario ajeno no puede consultar la lista."""

    response = client.get(
        f"/api/lists/{task_list.id}",
        headers=auth_headers(users[2]),
    )

    assert response.status_code == 404


def test_outsider_cannot_list_others_lists(
    client,
    users,
    task_list,
):
    """El listado no muestra listas ajenas."""

    response = client.get(
        "/api/lists",
        headers=auth_headers(users[2]),
    )

    assert response.status_code == 200

    visible_ids = {
        item["id"]
        for item in response.json()
    }

    assert task_list.id not in visible_ids


def test_member_can_read_shared_list(
    client,
    db_session,
    users,
    task_list,
):
    """Un colaborador puede consultar su lista compartida."""

    membership = ListMember(
        list_id=task_list.id,
        user_id=users[1].id,
        role="viewer",
    )

    db_session.add(membership)
    db_session.flush()

    response = client.get(
        f"/api/lists/{task_list.id}",
        headers=auth_headers(users[1]),
    )

    assert response.status_code == 200
    assert response.json()["id"] == task_list.id


def test_invalid_list_visibility(client, users):
    """La API rechaza visibilidades incorrectas."""

    response = client.post(
        "/api/lists",
        headers=auth_headers(users[0]),
        json={
            "name": "Lista incorrecta",
            "visibility": "public",
        },
    )

    assert response.status_code == 422

def test_owner_can_update_list(client, users, task_list):
    """El propietario puede editar su lista."""

    response = client.patch(
        f"/api/lists/{task_list.id}",
        headers=auth_headers(users[0]),
        json={"name": "Lista actualizada"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Lista actualizada"


def test_outsider_cannot_update_list(client, users, task_list):
    """Un usuario ajeno no puede editar la lista."""

    response = client.patch(
        f"/api/lists/{task_list.id}",
        headers=auth_headers(users[2]),
        json={"name": "Cambio no autorizado"},
    )

    assert response.status_code == 404


def test_owner_can_delete_list(client, users, task_list):
    """El propietario puede eliminar su lista."""

    response = client.delete(
        f"/api/lists/{task_list.id}",
        headers=auth_headers(users[0]),
    )

    assert response.status_code == 204

    response = client.get(
        f"/api/lists/{task_list.id}",
        headers=auth_headers(users[0]),
    )

    assert response.status_code == 404


def test_outsider_cannot_delete_list(client, users, task_list):
    """Un usuario ajeno no puede eliminar la lista."""

    response = client.delete(
        f"/api/lists/{task_list.id}",
        headers=auth_headers(users[2]),
    )

    assert response.status_code == 404


def test_list_name_cannot_be_null(client, users, task_list):
    """No se permite establecer un nombre nulo."""

    response = client.patch(
        f"/api/lists/{task_list.id}",
        headers=auth_headers(users[0]),
        json={"name": None},
    )

    assert response.status_code == 422


def test_list_visibility_cannot_be_null(client, users, task_list):
    """No se permite establecer una visibilidad nula."""

    response = client.patch(
        f"/api/lists/{task_list.id}",
        headers=auth_headers(users[0]),
        json={"visibility": None},
    )

    assert response.status_code == 422

def test_owner_can_add_member(client, users, task_list):
    """El propietario puede añadir colaboradores."""

    response = client.post(
        f"/api/lists/{task_list.id}/members",
        headers=auth_headers(users[0]),
        json={
            "user_id": users[1].id,
            "role": "editor",
        },
    )

    assert response.status_code == 201
    assert response.json()["user_id"] == users[1].id
    assert response.json()["role"] == "editor"


def test_outsider_cannot_add_member(client, users, task_list):
    """Un usuario ajeno no puede añadir colaboradores."""

    response = client.post(
        f"/api/lists/{task_list.id}/members",
        headers=auth_headers(users[2]),
        json={
            "user_id": users[1].id,
            "role": "editor",
        },
    )

    assert response.status_code == 404


def test_cannot_add_duplicate_member(
    client,
    users,
    task_list,
):
    """No se permite añadir dos veces al mismo usuario."""

    payload = {
        "user_id": users[1].id,
        "role": "viewer",
    }

    first_response = client.post(
        f"/api/lists/{task_list.id}/members",
        headers=auth_headers(users[0]),
        json=payload,
    )

    second_response = client.post(
        f"/api/lists/{task_list.id}/members",
        headers=auth_headers(users[0]),
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_cannot_add_owner_as_member(
    client,
    users,
    task_list,
):
    """El propietario no puede añadirse como miembro."""

    response = client.post(
        f"/api/lists/{task_list.id}/members",
        headers=auth_headers(users[0]),
        json={
            "user_id": users[0].id,
            "role": "editor",
        },
    )

    assert response.status_code == 409


def test_cannot_add_member_to_private_list(
    client,
    db_session,
    users,
    task_list,
):
    """Una lista privada no admite colaboradores."""

    task_list.visibility = "private"
    db_session.flush()

    response = client.post(
        f"/api/lists/{task_list.id}/members",
        headers=auth_headers(users[0]),
        json={
            "user_id": users[1].id,
            "role": "viewer",
        },
    )

    assert response.status_code == 409

def test_owner_can_list_members(
    client,
    db_session,
    users,
    task_list,
):
    """El propietario puede consultar los colaboradores."""

    member = ListMember(
        list_id=task_list.id,
        user_id=users[1].id,
        role="editor",
    )

    db_session.add(member)
    db_session.flush()

    response = client.get(
        f"/api/lists/{task_list.id}/members",
        headers=auth_headers(users[0]),
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["user_id"] == users[1].id


def test_member_can_list_members(
    client,
    db_session,
    users,
    task_list,
):
    """Un colaborador puede consultar los miembros."""

    member = ListMember(
        list_id=task_list.id,
        user_id=users[1].id,
        role="viewer",
    )

    db_session.add(member)
    db_session.flush()

    response = client.get(
        f"/api/lists/{task_list.id}/members",
        headers=auth_headers(users[1]),
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_outsider_cannot_list_members(
    client,
    users,
    task_list,
):
    """Un usuario ajeno no puede consultar colaboradores."""

    response = client.get(
        f"/api/lists/{task_list.id}/members",
        headers=auth_headers(users[2]),
    )

    assert response.status_code == 404

def test_owner_can_update_member_role(
    client,
    db_session,
    users,
    task_list,
):
    """El propietario puede cambiar el rol de un colaborador."""

    member = ListMember(
        list_id=task_list.id,
        user_id=users[1].id,
        role="viewer",
    )

    db_session.add(member)
    db_session.flush()

    response = client.patch(
        f"/api/lists/{task_list.id}/members/{users[1].id}",
        headers=auth_headers(users[0]),
        json={"role": "editor"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "editor"


def test_outsider_cannot_update_member_role(
    client,
    db_session,
    users,
    task_list,
):
    """Un usuario ajeno no puede modificar roles."""

    member = ListMember(
        list_id=task_list.id,
        user_id=users[1].id,
        role="viewer",
    )

    db_session.add(member)
    db_session.flush()

    response = client.patch(
        f"/api/lists/{task_list.id}/members/{users[1].id}",
        headers=auth_headers(users[2]),
        json={"role": "editor"},
    )

    assert response.status_code == 404


def test_cannot_assign_owner_role(
    client,
    db_session,
    users,
    task_list,
):
    """No se puede asignar el rol propietario a un colaborador."""

    member = ListMember(
        list_id=task_list.id,
        user_id=users[1].id,
        role="viewer",
    )

    db_session.add(member)
    db_session.flush()

    response = client.patch(
        f"/api/lists/{task_list.id}/members/{users[1].id}",
        headers=auth_headers(users[0]),
        json={"role": "owner"},
    )

    assert response.status_code == 422


def test_cannot_update_nonexistent_member(
    client,
    users,
    task_list,
):
    """No se puede modificar un colaborador inexistente."""

    response = client.patch(
        f"/api/lists/{task_list.id}/members/{users[2].id}",
        headers=auth_headers(users[0]),
        json={"role": "editor"},
    )

    assert response.status_code == 404

def test_owner_can_delete_member(
    client,
    db_session,
    users,
    task_list,
):
    """El propietario puede eliminar un colaborador."""

    member = ListMember(
        list_id=task_list.id,
        user_id=users[1].id,
        role="editor",
    )

    db_session.add(member)
    db_session.flush()

    response = client.delete(
        f"/api/lists/{task_list.id}/members/{users[1].id}",
        headers=auth_headers(users[0]),
    )

    assert response.status_code == 204

    deleted_member = db_session.scalar(
        select(ListMember).where(
            ListMember.list_id == task_list.id,
            ListMember.user_id == users[1].id,
        )
    )

    assert deleted_member is None


def test_outsider_cannot_delete_member(
    client,
    db_session,
    users,
    task_list,
):
    """Un usuario ajeno no puede eliminar colaboradores."""

    member = ListMember(
        list_id=task_list.id,
        user_id=users[1].id,
        role="viewer",
    )

    db_session.add(member)
    db_session.flush()

    response = client.delete(
        f"/api/lists/{task_list.id}/members/{users[1].id}",
        headers=auth_headers(users[2]),
    )

    assert response.status_code == 404


def test_cannot_delete_nonexistent_member(
    client,
    users,
    task_list,
):
    """No se puede eliminar un colaborador inexistente."""

    response = client.delete(
        f"/api/lists/{task_list.id}/members/{users[2].id}",
        headers=auth_headers(users[0]),
    )

    assert response.status_code == 404


def test_removed_member_loses_list_access(
    client,
    db_session,
    users,
    task_list,
):
    """Un colaborador eliminado pierde acceso a la lista."""

    member = ListMember(
        list_id=task_list.id,
        user_id=users[1].id,
        role="viewer",
    )

    db_session.add(member)
    db_session.flush()

    member_headers = auth_headers(users[1])
    owner_headers = auth_headers(users[0])

    before = client.get(
        f"/api/lists/{task_list.id}",
        headers=member_headers,
    )

    assert before.status_code == 200

    delete_response = client.delete(
        f"/api/lists/{task_list.id}/members/{users[1].id}",
        headers=owner_headers,
    )

    assert delete_response.status_code == 204

    after = client.get(
        f"/api/lists/{task_list.id}",
        headers=member_headers,
    )

    assert after.status_code == 404


def test_member_cannot_read_private_list(
    client,
    db_session,
    users,
    task_list,
):
    """Un colaborador no puede acceder a una lista privada."""

    member = ListMember(
        list_id=task_list.id,
        user_id=users[1].id,
        role="editor",
    )

    db_session.add(member)

    task_list.visibility = "private"
    db_session.flush()

    response = client.get(
        f"/api/lists/{task_list.id}",
        headers=auth_headers(users[1]),
    )

    assert response.status_code == 404


def test_private_list_hidden_from_member_listing(
    client,
    db_session,
    users,
    task_list,
):
    """Una lista privada no aparece entre las listas del colaborador."""

    member = ListMember(
        list_id=task_list.id,
        user_id=users[1].id,
        role="viewer",
    )

    db_session.add(member)

    task_list.visibility = "private"
    db_session.flush()

    response = client.get(
        "/api/lists",
        headers=auth_headers(users[1]),
    )

    assert response.status_code == 200

    list_ids = [
        item["id"]
        for item in response.json()
    ]

    assert task_list.id not in list_ids


def test_member_cannot_view_private_list_members(
    client,
    db_session,
    users,
    task_list,
):
    """Un colaborador no puede consultar miembros de una lista privada."""

    member = ListMember(
        list_id=task_list.id,
        user_id=users[1].id,
        role="viewer",
    )

    db_session.add(member)

    task_list.visibility = "private"
    db_session.flush()

    response = client.get(
        f"/api/lists/{task_list.id}/members",
        headers=auth_headers(users[1]),
    )

    assert response.status_code == 404
