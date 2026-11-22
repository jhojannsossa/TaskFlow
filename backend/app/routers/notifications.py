from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_current_user
from backend.app.database.connection import get_db
from backend.app.models.notification import Notification
from backend.app.models.notification_preference import NotificationPreference
from backend.app.models.user import User
from backend.app.schemas.notification import (
    NotificationResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
)


router = APIRouter(
    prefix="/api/notifications",
    tags=["Notifications"],
)


@router.get("", response_model=list[NotificationResponse])
def list_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve las notificaciones del usuario autenticado."""

    notifications = db.scalars(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(
            Notification.created_at.desc(),
            Notification.id.desc(),
        )
    ).all()

    return notifications


@router.patch("/read-all")
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Marca como leídas todas las notificaciones del usuario."""

    result = db.execute(
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )

    db.commit()

    return {
        "message": "Notificaciones marcadas como leídas.",
        "updated_count": result.rowcount,
    }


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
)
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Marca como leída una notificación propia."""

    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )

    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificación no encontrada.",
        )

    notification.is_read = True

    db.commit()
    db.refresh(notification)

    return notification


def get_or_create_preferences(
    db: Session,
    user_id: int,
) -> NotificationPreference:
    """Obtiene las preferencias o crea su configuración inicial."""

    preferences = db.get(NotificationPreference, user_id)

    if preferences is None:
        preferences = NotificationPreference(user_id=user_id)
        db.add(preferences)
        db.flush()

    return preferences


@router.get(
    "/preferences",
    response_model=NotificationPreferenceResponse,
)
def get_notification_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Consulta las preferencias del usuario."""

    preferences = get_or_create_preferences(
        db,
        current_user.id,
    )

    db.commit()
    db.refresh(preferences)

    return preferences


@router.patch(
    "/preferences",
    response_model=NotificationPreferenceResponse,
)
def update_notification_preferences(
    preferences_data: NotificationPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualiza las preferencias del usuario."""

    preferences = get_or_create_preferences(
        db,
        current_user.id,
    )

    changes = preferences_data.model_dump(
        exclude_unset=True,
        exclude_none=True,
    )

    for field, value in changes.items():
        setattr(preferences, field, value)

    db.commit()
    db.refresh(preferences)

    return preferences
