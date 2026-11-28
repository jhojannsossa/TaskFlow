from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    false,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base


class Notification(Base):
    """
    Modelo de notificaciones de TaskFlow.

    Permite gestionar notificaciones de tareas,
    listas compartidas y cumpleaños.
    """

    __tablename__ = "notifications"

    # Identificador de la notificación.
    id: Mapped[int] = mapped_column(
        Integer,
        Identity(),
        primary_key=True,
    )

    # Usuario que recibe la notificación.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    # Tarea relacionada, si existe.
    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Lista relacionada, si existe.
    list_id: Mapped[int | None] = mapped_column(
        ForeignKey("task_lists.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Usuario cuyo cumpleaños origina la notificación.
    birthday_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Año de celebración del cumpleaños.
    birthday_year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Tipo de notificación.
    type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    # Mensaje mostrado al usuario.
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Estado de lectura.
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=false(),
        nullable=False,
    )

    # Fecha de creación.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Evita notificaciones duplicadas de cumpleaños.
    __table_args__ = (
        Index(
            "uq_notifications_birthday_delivery",
            "user_id",
            "type",
            "birthday_user_id",
            "birthday_year",
            unique=True,
        ),
    )

    # Relación con el destinatario.
    user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="notifications",
    )

    # Relación con la tarea.
    task = relationship(
        "Task",
        back_populates="notifications",
    )

    # Relación con la lista.
    task_list = relationship(
        "TaskList",
        back_populates="notifications",
    )
