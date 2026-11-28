from sqlalchemy.orm import Session

from backend.app.models.notification import Notification
from backend.app.models.notification_preference import (
    NotificationPreference,
)


# Relación entre cada tipo de notificación
# y su preferencia de usuario.
NOTIFICATION_PREFERENCES = {
    "assignment": "assignments",
    "status_change": "status_changes",
    "shared_list_update": "shared_list_updates",
    "due_soon": "due_soon",
    "overdue": "overdue",
    "birthday_greeting": "birthday_greetings",
    "birthday_colleague": "birthday_colleagues",
}


def create_notification(
    db: Session,
    user_id: int,
    notification_type: str,
    message: str,
    task_id: int | None = None,
    list_id: int | None = None,
    *,
    birthday_user_id: int | None = None,
    birthday_year: int | None = None,
) -> Notification | None:
    """
    Crea una notificación si el usuario tiene
    activada la preferencia correspondiente.

    Para las notificaciones de cumpleaños,
    registra el usuario que cumple años y
    el año de la celebración.

    No realiza commit. La operación que llama
    a esta función controla la transacción.
    """

    # Comprobar que el tipo de notificación existe.
    preference_field = NOTIFICATION_PREFERENCES.get(
        notification_type
    )

    if preference_field is None:
        raise ValueError(
            f"Tipo de notificación no válido: {notification_type}"
        )

    # Comprobar la preferencia del destinatario.
    preferences = db.get(
        NotificationPreference,
        user_id,
    )

    if preferences is not None:
        is_enabled = getattr(
            preferences,
            preference_field,
        )

        if not is_enabled:
            return None

    # Identificar las notificaciones de cumpleaños.
    is_birthday_notification = notification_type in (
        "birthday_greeting",
        "birthday_colleague",
    )

    if is_birthday_notification:
        if birthday_user_id is None:
            raise ValueError(
                "La notificación de cumpleaños requiere "
                "birthday_user_id."
            )

        if birthday_year is None:
            raise ValueError(
                "La notificación de cumpleaños requiere "
                "birthday_year."
            )

    else:
        # Las notificaciones habituales no necesitan
        # información relacionada con cumpleaños.
        if birthday_user_id is not None:
            raise ValueError(
                "birthday_user_id solo se permite "
                "en notificaciones de cumpleaños."
            )

        if birthday_year is not None:
            raise ValueError(
                "birthday_year solo se permite "
                "en notificaciones de cumpleaños."
            )

    # Crear la notificación.
    notification = Notification(
        user_id=user_id,
        task_id=task_id,
        list_id=list_id,
        birthday_user_id=birthday_user_id,
        birthday_year=birthday_year,
        type=notification_type,
        message=message,
        is_read=False,
    )

    # Añadirla a la sesión.
    db.add(notification)

    return notification
