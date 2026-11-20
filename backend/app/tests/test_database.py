import pytest

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.database.connection import engine
from backend.app.models.user import User
from backend.app.models.task_list import TaskList
from backend.app.models.task import Task
from backend.app.models.list_member import ListMember


@pytest.fixture
def db_session():
    """Crea una sesión de prueba que revierte los cambios."""

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


def test_create_user(db_session):
    """Comprueba que podemos crear un usuario."""

    user = User(
        name="Carlos García",
        email="carlos.test@example.com",
        password_hash="hash_ficticio_para_pruebas",
    )

    db_session.add(user)
    db_session.flush()

    assert user.id is not None
    assert user.name == "Carlos García"


def test_create_task_with_list(db_session):
    """Comprueba las relaciones entre usuario, lista y tarea."""

    user = User(
        name="María López",
        email="maria.test@example.com",
        password_hash="hash_ficticio_para_pruebas",
    )

    db_session.add(user)
    db_session.flush()

    task_list = TaskList(
        owner_id=user.id,
        name="Proyecto Bootcamp",
        visibility="private",
    )

    db_session.add(task_list)
    db_session.flush()

    task = Task(
        list_id=task_list.id,
        created_by=user.id,
        title="Desarrollar backend",
        status="todo",
        priority="high",
    )

    db_session.add(task)
    db_session.flush()

    assert task.id is not None
    assert task.list_id == task_list.id
    assert task.created_by == user.id
    assert task.task_list.name == "Proyecto Bootcamp"


def test_duplicate_email_is_rejected(db_session):
    """Comprueba que no se permiten correos duplicados."""

    first_user = User(
        name="Usuario Uno",
        email="duplicado.test@example.com",
        password_hash="hash_ficticio_para_pruebas",
    )

    db_session.add(first_user)
    db_session.flush()

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            second_user = User(
                name="Usuario Dos",
                email="duplicado.test@example.com",
                password_hash="otro_hash_ficticio",
            )

            db_session.add(second_user)
            db_session.flush()


def test_invalid_task_status_is_rejected(db_session):
    """PostgreSQL debe rechazar estados de tarea inválidos."""

    user = User(
        name="Usuario Estados",
        email="estados.test@example.com",
        password_hash="hash_ficticio",
    )

    db_session.add(user)
    db_session.flush()

    task_list = TaskList(
        owner_id=user.id,
        name="Lista de estados",
    )

    db_session.add(task_list)
    db_session.flush()

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            task = Task(
                list_id=task_list.id,
                created_by=user.id,
                title="Tarea con estado inválido",
                status="cancelled",
            )

            db_session.add(task)
            db_session.flush()



def test_invalid_task_priority_is_rejected(db_session):
    """PostgreSQL debe rechazar prioridades no permitidas."""

    user = User(
        name="Usuario Prioridades",
        email="prioridades.test@example.com",
        password_hash="hash_ficticio",
    )

    db_session.add(user)
    db_session.flush()

    task_list = TaskList(
        owner_id=user.id,
        name="Lista de prioridades",
    )

    db_session.add(task_list)
    db_session.flush()

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            task = Task(
                list_id=task_list.id,
                created_by=user.id,
                title="Tarea con prioridad inválida",
                priority="extreme",
            )

            db_session.add(task)
            db_session.flush()


def test_duplicate_list_member_is_rejected(db_session):
    """Un usuario no puede pertenecer dos veces a la misma lista."""

    owner = User(
        name="Propietario",
        email="propietario.test@example.com",
        password_hash="hash_ficticio",
    )

    collaborator = User(
        name="Colaborador",
        email="colaborador.test@example.com",
        password_hash="hash_ficticio",
    )

    db_session.add_all([owner, collaborator])
    db_session.flush()

    task_list = TaskList(
        owner_id=owner.id,
        name="Lista compartida",
        visibility="shared",
    )

    db_session.add(task_list)
    db_session.flush()

    member = ListMember(
        list_id=task_list.id,
        user_id=collaborator.id,
        role="editor",
    )

    db_session.add(member)
    db_session.flush()

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            duplicate_member = ListMember(
                list_id=task_list.id,
                user_id=collaborator.id,
                role="viewer",
            )

            db_session.add(duplicate_member)
            db_session.flush()


def test_nonexistent_task_list_is_rejected(db_session):
    """Una tarea no puede apuntar a una lista inexistente."""

    user = User(
        name="Usuario Relaciones",
        email="relaciones.test@example.com",
        password_hash="hash_ficticio",
    )

    db_session.add(user)
    db_session.flush()

    nonexistent_list_id = db_session.execute(
        text("SELECT COALESCE(MAX(id), 0) + 1000000 FROM task_lists")
    ).scalar_one()

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            task = Task(
                list_id=nonexistent_list_id,
                created_by=user.id,
                title="Tarea sin lista válida",
            )

            db_session.add(task)
            db_session.flush()


def test_delete_list_cascades_to_tasks_and_members(db_session):
    """Eliminar una lista debe eliminar sus tareas y miembros."""

    owner = User(
        name="Propietario Cascade",
        email="cascade.owner@example.com",
        password_hash="hash_ficticio",
    )

    collaborator = User(
        name="Colaborador Cascade",
        email="cascade.member@example.com",
        password_hash="hash_ficticio",
    )

    db_session.add_all([owner, collaborator])
    db_session.flush()

    task_list = TaskList(
        owner_id=owner.id,
        name="Lista para eliminar",
        visibility="shared",
    )

    db_session.add(task_list)
    db_session.flush()

    task = Task(
        list_id=task_list.id,
        created_by=owner.id,
        title="Tarea para eliminar",
    )

    member = ListMember(
        list_id=task_list.id,
        user_id=collaborator.id,
        role="editor",
    )

    db_session.add_all([task, member])
    db_session.flush()

    list_id = task_list.id
    task_id = task.id
    member_id = member.id

    # Ejecutamos SQL directamente para probar la regla de PostgreSQL.
    db_session.execute(
        text("DELETE FROM task_lists WHERE id = :list_id"),
        {"list_id": list_id},
    )

    db_session.flush()

    remaining_task = db_session.execute(
        text("SELECT id FROM tasks WHERE id = :task_id"),
        {"task_id": task_id},
    ).scalar_one_or_none()

    remaining_member = db_session.execute(
        text("SELECT id FROM list_members WHERE id = :member_id"),
        {"member_id": member_id},
    ).scalar_one_or_none()

    assert remaining_task is None
    assert remaining_member is None


def test_delete_task_sets_activity_reference_to_null(db_session):
    """Eliminar una tarea conserva su actividad histórica."""

    user = User(
        name="Usuario Historial",
        email="historial.test@example.com",
        password_hash="hash_ficticio",
    )

    db_session.add(user)
    db_session.flush()

    task_list = TaskList(
        owner_id=user.id,
        name="Lista de historial",
    )

    db_session.add(task_list)
    db_session.flush()

    task = Task(
        list_id=task_list.id,
        created_by=user.id,
        title="Tarea con historial",
    )

    db_session.add(task)
    db_session.flush()

    # Creamos el registro histórico mediante SQL para centrarnos
    # en comprobar la clave foránea y su regla ON DELETE SET NULL.
    activity_id = db_session.execute(
        text("""
            INSERT INTO activity_logs (user_id, task_id, action)
            VALUES (:user_id, :task_id, :action)
            RETURNING id
        """),
        {
            "user_id": user.id,
            "task_id": task.id,
            "action": "task_created",
        },
    ).scalar_one()

    db_session.execute(
        text("DELETE FROM tasks WHERE id = :task_id"),
        {"task_id": task.id},
    )

    remaining_activity = db_session.execute(
        text("""
            SELECT task_id
            FROM activity_logs
            WHERE id = :activity_id
        """),
        {"activity_id": activity_id},
    ).one_or_none()

    assert remaining_activity is not None
    assert remaining_activity.task_id is None
