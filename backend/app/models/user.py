from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Identity,
    Integer,
    String,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        Identity(),
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    owned_lists = relationship(
        "TaskList",
        back_populates="owner",
    )
    # ORM relationships
    created_tasks = relationship(
        "Task",
        foreign_keys="Task.created_by",
        back_populates="creator",
    )

    assigned_tasks = relationship(
        "Task",
        foreign_keys="Task.assigned_to",
        back_populates="assignee",
    )

    memberships = relationship(
        "ListMember",
        back_populates="user",
    )

    notifications = relationship(
        "Notification",
        back_populates="user",
    )

    activity_logs = relationship(
        "ActivityLog",
        back_populates="user",
    )

    notification_preference = relationship(
        "NotificationPreference",
        back_populates="user",
        uselist=False,
    )
