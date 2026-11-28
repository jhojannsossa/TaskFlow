from datetime import date

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.app.models.list_member import ListMember
from backend.app.models.notification import Notification
from backend.app.models.task_list import TaskList
from backend.app.models.user import User
from backend.app.services.notification_service import (
    create_notification,
)


# Identificador reservado para el proceso de cumpleaños.
BIRTHDAY_LOCK_ID = 280028


def is_birthday_today(
    birth_date: date | None,
    today: date | None = None,
) -> bool:
    """
    Comprueba si una persona cumple años
    en la fecha indicada.

    Los nacidos el 29 de febrero celebran
    el 28 de febrero en años no bisiestos.
    """

    if birth_date is None:
        return False

    if today is None:
        today = date.today()

    if (
        birth_date.month == today.month
        and birth_date.day == today.day
    ):
        return True

    if birth_date.month == 2 and birth_date.day == 29:
        is_leap_year = (
            today.year % 4 == 0
            and (
                today.year % 100 != 0
                or today.year % 400 == 0
            )
        )

        if not is_leap_year:
            return (
                today.month == 2
                and today.day == 28
            )

    return False


def get_birthday_colleagues(
    db: Session,
    birthday_user_id: int,
) -> list[int]:
    """
    Devuelve los identificadores de compañeros
    que comparten al menos una lista con el usuario.

    Solo considera listas compartidas.
    Excluye al propio cumpleañero.
    Excluye usuarios inactivos.
    No devuelve duplicados.
    """

    owned_list_ids = select(TaskList.id).where(
        TaskList.owner_id == birthday_user_id,
        TaskList.visibility == "shared",
    )

    member_list_ids = (
        select(ListMember.list_id)
        .join(
            TaskList,
            TaskList.id == ListMember.list_id,
        )
        .where(
            ListMember.user_id == birthday_user_id,
            TaskList.visibility == "shared",
        )
    )

    shared_list_ids = (
        owned_list_ids
        .union(member_list_ids)
        .subquery()
    )

    owner_ids = (
        select(TaskList.owner_id.label("user_id"))
        .where(
            TaskList.id.in_(
                select(shared_list_ids.c.id)
            )
        )
    )

    member_ids = (
        select(ListMember.user_id.label("user_id"))
        .where(
            ListMember.list_id.in_(
                select(shared_list_ids.c.id)
            )
        )
    )

    colleague_ids = (
        owner_ids
        .union(member_ids)
        .subquery()
    )

    result = db.scalars(
        select(User.id)
        .where(
            User.id.in_(
                select(colleague_ids.c.user_id)
            ),
            User.id != birthday_user_id,
            User.is_active.is_(True),
        )
        .order_by(User.id)
    ).all()

    return list(result)


def birthday_notification_exists(
    db: Session,
    user_id: int,
    notification_type: str,
    birthday_user_id: int,
    birthday_year: int,
) -> bool:
    """
    Comprueba si ya existe una notificación
    para el mismo destinatario, tipo,
    cumpleañero y año.
    """

    statement = (
        select(Notification.id)
        .where(
            Notification.user_id == user_id,
            Notification.type == notification_type,
            Notification.birthday_user_id
            == birthday_user_id,
            Notification.birthday_year
            == birthday_year,
        )
        .limit(1)
    )

    return db.scalar(statement) is not None


def acquire_birthday_lock(db: Session) -> None:
    """
    Adquiere un bloqueo transaccional de PostgreSQL.

    Si otro proceso mantiene este mismo bloqueo,
    espera hasta que termine su transacción.

    El bloqueo se libera automáticamente
    al hacer commit o rollback.

    Todos los procesos de cumpleaños deben
    utilizar este mecanismo.
    """

    db.execute(
        text(
            "SELECT pg_advisory_xact_lock(:lock_id)"
        ),
        {"lock_id": BIRTHDAY_LOCK_ID},
    )


def process_birthday_notifications(
    db: Session,
    today: date | None = None,
) -> int:
    """
    Genera las notificaciones de cumpleaños
    correspondientes a la fecha indicada.

    Felicita personalmente al cumpleañero.

    Avisa a sus compañeros únicamente cuando
    el usuario permite compartir su cumpleaños.

    Respeta las preferencias del destinatario.

    Evita notificaciones duplicadas.

    Utiliza un bloqueo transaccional para
    coordinar ejecuciones simultáneas.

    No realiza commit. El llamador controla
    la transacción y debe finalizarla.

    Devuelve el número de notificaciones creadas.
    """

    if today is None:
        today = date.today()

    # Proteger el procesamiento frente a
    # ejecuciones simultáneas.
    acquire_birthday_lock(db)

    created_count = 0

    users = db.scalars(
        select(User)
        .where(
            User.is_active.is_(True),
            User.birth_date.is_not(None),
        )
        .order_by(User.id)
    ).all()

    processed_keys = set()

    for birthday_user in users:

        if not is_birthday_today(
            birthday_user.birth_date,
            today,
        ):
            continue

        birthday_user_id = birthday_user.id
        birthday_year = today.year

        # 1. Felicitación personal.
        greeting_type = "birthday_greeting"

        greeting_key = (
            birthday_user_id,
            greeting_type,
            birthday_user_id,
            birthday_year,
        )

        greeting_exists = birthday_notification_exists(
            db=db,
            user_id=birthday_user_id,
            notification_type=greeting_type,
            birthday_user_id=birthday_user_id,
            birthday_year=birthday_year,
        )

        if (
            greeting_key not in processed_keys
            and not greeting_exists
        ):
            notification = create_notification(
                db=db,
                user_id=birthday_user_id,
                notification_type=greeting_type,
                message=(
                    "¡Feliz cumpleaños! "
                    "Todo el equipo de TaskFlow "
                    "te desea un excelente día."
                ),
                birthday_user_id=birthday_user_id,
                birthday_year=birthday_year,
            )

            if notification is not None:
                processed_keys.add(greeting_key)
                created_count += 1

        # 2. Respetar la privacidad.
        if not birthday_user.share_birthday:
            continue

        # 3. Identificar compañeros.
        colleague_ids = get_birthday_colleagues(
            db=db,
            birthday_user_id=birthday_user_id,
        )

        # 4. Crear avisos para los compañeros.
        for colleague_id in colleague_ids:

            colleague_type = "birthday_colleague"

            colleague_key = (
                colleague_id,
                colleague_type,
                birthday_user_id,
                birthday_year,
            )

            if colleague_key in processed_keys:
                continue

            if birthday_notification_exists(
                db=db,
                user_id=colleague_id,
                notification_type=colleague_type,
                birthday_user_id=birthday_user_id,
                birthday_year=birthday_year,
            ):
                continue

            notification = create_notification(
                db=db,
                user_id=colleague_id,
                notification_type=colleague_type,
                message=(
                    f"¡Hoy es el cumpleaños de "
                    f"{birthday_user.name}! "
                    "Puedes enviarle una felicitación."
                ),
                birthday_user_id=birthday_user_id,
                birthday_year=birthday_year,
            )

            if notification is not None:
                processed_keys.add(colleague_key)
                created_count += 1

    # Enviar los cambios a PostgreSQL.
    # El commit lo realizará el llamador.
    db.flush()

    return created_count