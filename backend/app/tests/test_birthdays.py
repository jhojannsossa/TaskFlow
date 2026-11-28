import uuid
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.connection import engine
from backend.app.models.list_member import ListMember
from backend.app.models.notification import Notification
from backend.app.models.notification_preference import (
    NotificationPreference,
)
from backend.app.models.task_list import TaskList
from backend.app.models.user import User
from backend.app.services.birthday_service import (
    get_birthday_colleagues,
    is_birthday_today,
    process_birthday_notifications,
)


TEST_DATE = date(2032, 6, 15)


@pytest.fixture
def db_session():
    """
    Crea una sesión de prueba.

    Todos los cambios se revierten al finalizar.
    """

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


def create_test_user(
    db: Session,
    name: str,
    birth_date: date | None = None,
    share_birthday: bool = False,
    is_active: bool = True,
) -> User:
    """
    Crea un usuario con correo único
    para evitar conflictos entre pruebas.
    """

    user = User(
        name=name,
        email=f"{uuid.uuid4().hex}@example.com",
        password_hash="hash_de_prueba",
        birth_date=birth_date,
        share_birthday=share_birthday,
        is_active=is_active,
    )

    db.add(user)
    db.flush()

    return user


def create_shared_list(
    db: Session,
    owner: User,
    collaborator: User,
    visibility: str = "shared",
) -> TaskList:
    """
    Crea una lista y añade un colaborador.
    """

    task_list = TaskList(
        owner_id=owner.id,
        name=f"Lista de prueba {uuid.uuid4().hex[:8]}",
        visibility=visibility,
    )

    db.add(task_list)
    db.flush()

    membership = ListMember(
        list_id=task_list.id,
        user_id=collaborator.id,
        role="editor",
    )

    db.add(membership)
    db.flush()

    return task_list


def get_birthday_notifications(
    db: Session,
    birthday_user_id: int,
) -> list[Notification]:
    """
    Consulta las notificaciones generadas
    para un cumpleañero concreto.
    """

    return list(
        db.scalars(
            select(Notification)
            .where(
                Notification.birthday_user_id
                == birthday_user_id,
            )
            .order_by(Notification.id)
        ).all()
    )


def test_normal_birthday():
    assert is_birthday_today(
        date(1995, 6, 15),
        TEST_DATE,
    )

    assert not is_birthday_today(
        date(1995, 6, 16),
        TEST_DATE,
    )

    assert not is_birthday_today(
        None,
        TEST_DATE,
    )


def test_february_29_birthday():
    birth_date = date(2000, 2, 29)

    # Año no bisiesto.
    assert is_birthday_today(
        birth_date,
        date(2031, 2, 28),
    )

    # Año bisiesto.
    assert is_birthday_today(
        birth_date,
        date(2032, 2, 29),
    )

    # En año bisiesto no se adelanta.
    assert not is_birthday_today(
        birth_date,
        date(2032, 2, 28),
    )


def test_personal_birthday_greeting(db_session):
    user = create_test_user(
        db_session,
        "Cumpleañero personal",
        birth_date=date(1995, 6, 15),
        share_birthday=False,
    )

    process_birthday_notifications(
        db_session,
        today=TEST_DATE,
    )

    notifications = get_birthday_notifications(
        db_session,
        user.id,
    )

    assert len(notifications) == 1

    notification = notifications[0]

    assert notification.user_id == user.id
    assert notification.type == "birthday_greeting"
    assert notification.birthday_year == 2032
    assert notification.is_read is False


def test_colleagues_receive_birthday_alert(db_session):
    birthday_user = create_test_user(
        db_session,
        "Cumpleañero compartido",
        birth_date=date(1995, 6, 15),
        share_birthday=True,
    )

    colleague = create_test_user(
        db_session,
        "Compañero de equipo",
    )

    create_shared_list(
        db_session,
        birthday_user,
        colleague,
    )

    colleague_ids = get_birthday_colleagues(
        db_session,
        birthday_user.id,
    )

    assert colleague.id in colleague_ids

    process_birthday_notifications(
        db_session,
        today=TEST_DATE,
    )

    notifications = get_birthday_notifications(
        db_session,
        birthday_user.id,
    )

    assert len(notifications) == 2

    greeting = next(
        notification
        for notification in notifications
        if notification.type == "birthday_greeting"
    )

    colleague_alert = next(
        notification
        for notification in notifications
        if notification.type == "birthday_colleague"
    )

    assert greeting.user_id == birthday_user.id
    assert colleague_alert.user_id == colleague.id
    assert birthday_user.name in colleague_alert.message

    # No debe mostrar la edad ni el año de nacimiento.
    assert "1995" not in colleague_alert.message


def test_private_birthday_does_not_alert_colleagues(
    db_session,
):
    birthday_user = create_test_user(
        db_session,
        "Cumpleañero privado",
        birth_date=date(1995, 6, 15),
        share_birthday=False,
    )

    colleague = create_test_user(
        db_session,
        "Compañero sin aviso",
    )

    create_shared_list(
        db_session,
        birthday_user,
        colleague,
    )

    process_birthday_notifications(
        db_session,
        today=TEST_DATE,
    )

    notifications = get_birthday_notifications(
        db_session,
        birthday_user.id,
    )

    assert len(notifications) == 1
    assert notifications[0].type == "birthday_greeting"
    assert notifications[0].user_id == birthday_user.id


def test_disabled_greeting_preference(db_session):
    birthday_user = create_test_user(
        db_session,
        "Usuario sin felicitación",
        birth_date=date(1995, 6, 15),
    )

    preference = NotificationPreference(
        user_id=birthday_user.id,
        birthday_greetings=False,
    )

    db_session.add(preference)
    db_session.flush()

    process_birthday_notifications(
        db_session,
        today=TEST_DATE,
    )

    notifications = get_birthday_notifications(
        db_session,
        birthday_user.id,
    )

    assert notifications == []


def test_disabled_colleague_preference(db_session):
    birthday_user = create_test_user(
        db_session,
        "Cumpleañero con compañeros",
        birth_date=date(1995, 6, 15),
        share_birthday=True,
    )

    colleague = create_test_user(
        db_session,
        "Compañero con avisos desactivados",
    )

    create_shared_list(
        db_session,
        birthday_user,
        colleague,
    )

    preference = NotificationPreference(
        user_id=colleague.id,
        birthday_colleagues=False,
    )

    db_session.add(preference)
    db_session.flush()

    process_birthday_notifications(
        db_session,
        today=TEST_DATE,
    )

    notifications = get_birthday_notifications(
        db_session,
        birthday_user.id,
    )

    assert len(notifications) == 1
    assert notifications[0].type == "birthday_greeting"
    assert notifications[0].user_id == birthday_user.id


def test_birthday_notifications_are_not_duplicated(
    db_session,
):
    birthday_user = create_test_user(
        db_session,
        "Cumpleañero sin duplicados",
        birth_date=date(1995, 6, 15),
        share_birthday=True,
    )

    colleague = create_test_user(
        db_session,
        "Compañero sin duplicados",
    )

    create_shared_list(
        db_session,
        birthday_user,
        colleague,
    )

    process_birthday_notifications(
        db_session,
        today=TEST_DATE,
    )

    first_notifications = get_birthday_notifications(
        db_session,
        birthday_user.id,
    )

    assert len(first_notifications) == 2

    second_count = process_birthday_notifications(
        db_session,
        today=TEST_DATE,
    )

    second_notifications = get_birthday_notifications(
        db_session,
        birthday_user.id,
    )

    assert second_count == 0
    assert len(second_notifications) == 2


def test_inactive_users_are_not_notified(db_session):
    birthday_user = create_test_user(
        db_session,
        "Cumpleañero activo",
        birth_date=date(1995, 6, 15),
        share_birthday=True,
    )

    inactive_colleague = create_test_user(
        db_session,
        "Compañero inactivo",
        is_active=False,
    )

    create_shared_list(
        db_session,
        birthday_user,
        inactive_colleague,
    )

    colleague_ids = get_birthday_colleagues(
        db_session,
        birthday_user.id,
    )

    assert inactive_colleague.id not in colleague_ids

    process_birthday_notifications(
        db_session,
        today=TEST_DATE,
    )

    notifications = get_birthday_notifications(
        db_session,
        birthday_user.id,
    )

    assert len(notifications) == 1
    assert notifications[0].user_id == birthday_user.id