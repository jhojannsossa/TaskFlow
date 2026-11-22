from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    """Representa una notificación recibida por el usuario."""

    id: int
    user_id: int
    task_id: int | None
    list_id: int | None
    type: str
    message: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferenceResponse(BaseModel):
    """Devuelve las preferencias actuales del usuario."""

    user_id: int
    due_soon: bool
    overdue: bool
    status_changes: bool
    assignments: bool
    shared_list_updates: bool
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferenceUpdate(BaseModel):
    """Permite modificar una o varias preferencias."""

    due_soon: bool | None = None
    overdue: bool | None = None
    status_changes: bool | None = None
    assignments: bool | None = None
    shared_list_updates: bool | None = None