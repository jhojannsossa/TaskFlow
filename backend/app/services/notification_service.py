from sqlalchemy.orm import Session

from backend.app.models.notification import Notification
from backend.app.models.notification_preference import NotificationPreference


NOTIFICATION_PREFERENCES = {
    "assignment": "assignments",
    "status_change": "status_changes",
    "shared_list_update": "shared_list_updates",
    "due_soon": "due_soon",
    "overdue": "overdue",
}


def create_notification(
    db: Session,
    user_id: int,
    notification_type: str,
    message: str,
    task_id: int | None = None,
    list_id: int | None = None,
) -> Notification | None:
    """
    Crea una notificación si el usuario tiene
    activada la preferencia correspondiente.

    No realiza commit: la operación que llama
    a esta función controla la transacción.
    """

    preference_field = NOTIFICATION_PREFERENCES.get(
        notification_type
    )

    if preference_field is None:
        raise ValueError(
            f"Tipo de notificación no válido: {notification_type}"
        )

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

    notification = Notification(
        user_id=user_id,
        task_id=task_id,
        list_id=list_id,
        type=notification_type,
        message=message,
        is_read=False,
    )

    db.add(notification)

    return notification