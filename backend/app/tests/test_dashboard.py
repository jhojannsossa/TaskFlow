import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.database.connection import engine, get_db
from backend.app.core.security import create_access_token

from backend.app.models.user import User
from backend.app.models.task import Task
from backend.app.models.activity import ActivityLog
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

    for name in ["Propietario dashboard", "Usuario externo"]:
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
def task_data(db_session, users):
    owner, outsider = users

    own_list = TaskList(
        owner_id=owner.id,
        name="Lista principal dashboard",
        visibility="private",
    )

    other_list = TaskList(
        owner_id=outsider.id,
        name="Lista privada externa",
        visibility="private",
    )

    db_session.add_all([own_list, other_list])
    db_session.flush()

    tasks = [
        Task(
            list_id=own_list.id,
            created_by=owner.id,
            title="Tarea pendiente",
            status="todo",
        ),
        Task(
            list_id=own_list.id,
            created_by=owner.id,
            title="Tarea en progreso",
            status="in_progress",
        ),
        Task(
            list_id=own_list.id,
            created_by=owner.id,
            title="Tarea terminada",
            status="done",
        ),
        Task(
            list_id=other_list.id,
            created_by=outsider.id,
            title="Tarea privada externa",
            status="todo",
        ),
    ]

    db_session.add_all(tasks)
    db_session.flush()

    return own_list, other_list, tasks


def auth_headers(user):
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


def test_dashboard_requires_authentication(client):
    endpoints = [
        "/api/dashboard/tasks-by-status",
        "/api/dashboard/tasks-by-list",
        "/api/dashboard/weekly",
        "/api/dashboard/recent-activity",
    ]

    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code == 401


def test_dashboard_tasks_by_status(client, users, task_data):
    response = client.get(
        "/api/dashboard/tasks-by-status",
        headers=auth_headers(users[0]),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["todo"] == 1
    assert data["in_progress"] == 1
    assert data["done"] == 1


def test_dashboard_tasks_by_list(client, users, task_data):
    own_list, other_list, _ = task_data

    response = client.get(
        "/api/dashboard/tasks-by-list",
        headers=auth_headers(users[0]),
    )

    assert response.status_code == 200

    data = response.json()

    own = next(
        item for item in data
        if item["list_id"] == own_list.id
    )

    assert own["total_tasks"] == 3

    returned_ids = {item["list_id"] for item in data}

    assert other_list.id not in returned_ids


def test_dashboard_weekly_statistics(client, users, task_data):
    response = client.get(
        "/api/dashboard/weekly?weeks=4",
        headers=auth_headers(users[0]),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 4

    for week in data:
        assert "week_start" in week
        assert "created" in week
        assert "completed" in week


def test_dashboard_recent_activity(client, users):
    response = client.get(
        "/api/dashboard/recent-activity",
        headers=auth_headers(users[0]),
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_dashboard_rejects_invalid_parameters(client, users):
    headers = auth_headers(users[0])

    response = client.get(
        "/api/dashboard/weekly?weeks=0",
        headers=headers,
    )

    assert response.status_code == 422

    response = client.get(
        "/api/dashboard/recent-activity?limit=101",
        headers=headers,
    )

    assert response.status_code == 422


def test_shared_list_is_visible_to_member(
    client,
    db_session,
    users,
):
    owner, collaborator = users

    shared_list = TaskList(
        owner_id=owner.id,
        name="Lista compartida dashboard",
        visibility="shared",
    )

    db_session.add(shared_list)
    db_session.flush()

    membership = ListMember(
        list_id=shared_list.id,
        user_id=collaborator.id,
        role="editor",
    )

    task = Task(
        list_id=shared_list.id,
        created_by=owner.id,
        title="Tarea compartida",
        status="todo",
    )

    db_session.add_all([membership, task])
    db_session.flush()

    response = client.get(
        "/api/dashboard/tasks-by-list",
        headers=auth_headers(collaborator),
    )

    assert response.status_code == 200

    returned_ids = {
        item["list_id"]
        for item in response.json()
    }

    assert shared_list.id in returned_ids

def test_task_creation_registers_activity(
    client,
    db_session,
    users,
):
    """Crear una tarea debe generar actividad visible en el dashboard."""

    owner = users[0]

    # Crear una lista para la prueba.
    task_list = TaskList(
        owner_id=owner.id,
        name="Lista para probar actividad",
        visibility="private",
    )

    db_session.add(task_list)
    db_session.flush()

    # Crear una tarea mediante la API.
    response = client.post(
        "/api/tasks",
        headers=auth_headers(owner),
        json={
            "list_id": task_list.id,
            "title": "Probar historial de actividad",
        },
    )

    assert response.status_code == 201

    task_id = response.json()["id"]

    # Comprobar que se guardó el evento en PostgreSQL.
    activity = db_session.query(ActivityLog).filter_by(
        task_id=task_id,
        user_id=owner.id,
        action="task_created",
    ).first()

    assert activity is not None
    assert activity.list_id == task_list.id
    assert activity.details["title"] == "Probar historial de actividad"

    # Comprobar que el dashboard muestra el evento.
    dashboard_response = client.get(
        "/api/dashboard/recent-activity",
        headers=auth_headers(owner),
    )

    assert dashboard_response.status_code == 200

    activity_ids = {
        item["id"]
        for item in dashboard_response.json()
    }

    assert activity.id in activity_ids

def test_task_status_change_registers_activity(
    client,
    db_session,
    users,
):
    """Cambiar el estado de una tarea debe generar un evento."""

    owner = users[0]

    # Crear una lista de prueba.
    task_list = TaskList(
        owner_id=owner.id,
        name="Lista para probar cambios de estado",
        visibility="private",
    )

    db_session.add(task_list)
    db_session.flush()

    # Crear una tarea usando la API.
    create_response = client.post(
        "/api/tasks",
        headers=auth_headers(owner),
        json={
            "list_id": task_list.id,
            "title": "Tarea para actualizar",
            "status": "todo",
        },
    )

    assert create_response.status_code == 201

    task_id = create_response.json()["id"]

    # Cambiar el estado de la tarea.
    update_response = client.patch(
        f"/api/tasks/{task_id}",
        headers=auth_headers(owner),
        json={
            "status": "done",
        },
    )

    assert update_response.status_code == 200

    # Comprobar el registro de actividad.
    activity = db_session.query(ActivityLog).filter_by(
        task_id=task_id,
        user_id=owner.id,
        action="task_status_changed",
    ).first()

    assert activity is not None
    assert activity.details["previous_status"] == "todo"
    assert activity.details["new_status"] == "done"
    assert "status" in activity.details["changed_fields"]

def test_task_deletion_registers_activity(
    client,
    db_session,
    users,
):
    """Eliminar una tarea debe conservar un registro de actividad."""

    owner = users[0]

    # Crear una lista de prueba.
    task_list = TaskList(
        owner_id=owner.id,
        name="Lista para probar eliminaciones",
        visibility="private",
    )

    db_session.add(task_list)
    db_session.flush()

    # Crear una tarea mediante la API.
    create_response = client.post(
        "/api/tasks",
        headers=auth_headers(owner),
        json={
            "list_id": task_list.id,
            "title": "Tarea que será eliminada",
        },
    )

    assert create_response.status_code == 201

    task_id = create_response.json()["id"]

    # Eliminar la tarea.
    delete_response = client.delete(
        f"/api/tasks/{task_id}",
        headers=auth_headers(owner),
    )

    assert delete_response.status_code in (200, 204)

    # Verificar que se conservó el evento de eliminación.
    activity = db_session.query(ActivityLog).filter_by(
        user_id=owner.id,
        action="task_deleted",
    ).filter(
        ActivityLog.details["deleted_task_id"].as_integer()
        == task_id
    ).first()

    assert activity is not None
    assert activity.task_id is None
    assert activity.list_id == task_list.id
    assert activity.details["title"] == "Tarea que será eliminada"

    # Verificar que aparece en la actividad reciente.
    dashboard_response = client.get(
        "/api/dashboard/recent-activity",
        headers=auth_headers(owner),
    )

    assert dashboard_response.status_code == 200

    activity_ids = {
        item["id"]
        for item in dashboard_response.json()
    }

    assert activity.id in activity_ids

def test_list_deletion_registers_activity(
    client,
    db_session,
    users,
):
    """Eliminar una lista debe conservar su historial."""

    owner = users[0]

    # Crear una lista mediante la API.
    create_response = client.post(
        "/api/lists",
        headers=auth_headers(owner),
        json={
            "name": "Lista que será eliminada",
            "visibility": "private",
        },
    )

    assert create_response.status_code == 201

    list_id = create_response.json()["id"]

    # Eliminar la lista.
    delete_response = client.delete(
        f"/api/lists/{list_id}",
        headers=auth_headers(owner),
    )

    assert delete_response.status_code in (200, 204)

    # Comprobar que la lista ya no existe.
    deleted_list = db_session.get(TaskList, list_id)

    assert deleted_list is None

    # Buscar el evento de eliminación en PostgreSQL.
    activity = (
        db_session.query(ActivityLog)
        .filter_by(
            user_id=owner.id,
            action="list_deleted",
        )
        .filter(
            ActivityLog.details["deleted_list_id"].as_integer()
            == list_id
        )
        .first()
    )

    assert activity is not None
    assert activity.list_id is None
    assert activity.details["name"] == "Lista que será eliminada"
    assert activity.details["visibility"] == "private"

    # Comprobar que el dashboard muestra el evento.
    dashboard_response = client.get(
        "/api/dashboard/recent-activity",
        headers=auth_headers(owner),
    )

    assert dashboard_response.status_code == 200

    activity_ids = {
        item["id"]
        for item in dashboard_response.json()
    }

    assert activity.id in activity_ids

def test_private_list_is_hidden_from_member_dashboard(
    client,
    db_session,
    users,
):
    """Una lista privada no debe aparecer en las estadísticas del colaborador."""

    owner = users[0]
    member = users[1]

    # Crear una lista compartida.
    task_list = TaskList(
        owner_id=owner.id,
        name="Lista de privacidad del dashboard",
        visibility="shared",
    )

    db_session.add(task_list)
    db_session.flush()

    # Añadir un colaborador a la lista.
    membership = ListMember(
        list_id=task_list.id,
        user_id=member.id,
        role="viewer",
    )

    db_session.add(membership)
    db_session.flush()

    # Crear una tarea en esa lista.
    task = Task(
        list_id=task_list.id,
        created_by=owner.id,
        title="Tarea de privacidad",
        status="todo",
    )

    db_session.add(task)
    db_session.commit()

    # El colaborador puede consultar la lista compartida.
    shared_response = client.get(
        "/api/dashboard/tasks-by-list",
        headers=auth_headers(member),
    )

    assert shared_response.status_code == 200

    # Cambiar la lista a privada.
    task_list.visibility = "private"
    db_session.commit()

    # El colaborador ya no debe ver sus estadísticas.
    private_response = client.get(
        "/api/dashboard/tasks-by-list",
        headers=auth_headers(member),
    )

    assert private_response.status_code == 200

    # Comprobar que la lista privada no aparece.
    private_data = private_response.json()

    assert not any(
        item["list_id"] == task_list.id
        for item in private_data
    )

def test_weekly_statistics_counts_created_and_completed_tasks(
    client,
    db_session,
    users,
):
    """Comprueba los recuentos semanales de tareas."""

    owner = users[0]

    # Obtener el lunes de la semana actual en UTC.
    now = datetime.now(timezone.utc)
    current_monday = (
        now - timedelta(days=now.weekday())
    ).replace(hour=0, minute=0, second=0, microsecond=0)

    previous_monday = current_monday - timedelta(weeks=1)

    # Crear una lista privada del propietario.
    task_list = TaskList(
        owner_id=owner.id,
        name="Lista de estadísticas semanales",
        visibility="private",
    )

    db_session.add(task_list)
    db_session.flush()

    # Dos tareas creadas la semana anterior.
    task_1 = Task(
        list_id=task_list.id,
        created_by=owner.id,
        title="Tarea completada",
        status="done",
        created_at=previous_monday + timedelta(days=1),
        completed_at=current_monday + timedelta(days=1),
    )

    task_2 = Task(
        list_id=task_list.id,
        created_by=owner.id,
        title="Tarea pendiente",
        status="todo",
        created_at=previous_monday + timedelta(days=2),
        completed_at=None,
    )

    # Una tarea creada durante la semana actual.
    task_3 = Task(
        list_id=task_list.id,
        created_by=owner.id,
        title="Tarea actual",
        status="todo",
        created_at=current_monday + timedelta(days=1),
        completed_at=None,
    )

    db_session.add_all([task_1, task_2, task_3])
    db_session.commit()

    # Consultar las estadísticas de las últimas 2 semanas.
    response = client.get(
        "/api/dashboard/weekly?weeks=2",
        headers=auth_headers(owner),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2

    previous_week = data[0]
    current_week = data[1]

    # Comprobar las fechas de inicio.
    assert previous_week["week_start"] == (
        previous_monday.date().isoformat()
    )

    assert current_week["week_start"] == (
        current_monday.date().isoformat()
    )

    # Semana anterior: 2 creadas, 0 completadas.
    assert previous_week["created"] == 2
    assert previous_week["completed"] == 0

    # Semana actual: 1 creada, 1 completada.
    assert current_week["created"] == 1
    assert current_week["completed"] == 1

def test_recent_activity_hidden_after_member_loses_access(
    client,
    db_session,
    users,
):
    """Un colaborador no ve actividad de listas a las que perdió acceso."""

    owner = users[0]
    member = users[1]

    # Crear una lista compartida.
    task_list = TaskList(
        owner_id=owner.id,
        name="Lista de privacidad de actividad",
        visibility="shared",
    )

    db_session.add(task_list)
    db_session.flush()

    # Añadir un colaborador.
    membership = ListMember(
        list_id=task_list.id,
        user_id=member.id,
        role="viewer",
    )

    db_session.add(membership)
    db_session.flush()

    # Registrar una actividad del propietario en la lista.
    activity = ActivityLog(
        user_id=owner.id,
        list_id=task_list.id,
        action="list_updated",
        details={"name": task_list.name},
    )

    db_session.add(activity)
    db_session.commit()

    activity_id = activity.id

    # El colaborador puede ver la actividad compartida.
    shared_response = client.get(
        "/api/dashboard/recent-activity",
        headers=auth_headers(member),
    )

    assert shared_response.status_code == 200

    shared_activity_ids = [
        item["id"]
        for item in shared_response.json()
    ]

    assert activity_id in shared_activity_ids

    # Eliminar al colaborador de la lista.
    db_session.delete(membership)
    db_session.commit()

    # El colaborador ya no debe ver esa actividad.
    private_response = client.get(
        "/api/dashboard/recent-activity",
        headers=auth_headers(member),
    )

    assert private_response.status_code == 200

    private_activity_ids = [
        item["id"]
        for item in private_response.json()
    ]

    assert activity_id not in private_activity_ids
