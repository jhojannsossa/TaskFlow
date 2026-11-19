from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base
from backend.app.models.enums import ListVisibility


class TaskList(Base):
    __tablename__ = "task_lists"

    __table_args__ = (
        CheckConstraint(
            "visibility IN ('private', 'shared')",
            name="ck_task_lists_visibility",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        Identity(),
        primary_key=True,
    )

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    visibility: Mapped[str] = mapped_column(
        String(10),
        default=ListVisibility.PRIVATE.value,
        server_default=ListVisibility.PRIVATE.value,
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
    # ORM relationships
    owner = relationship(
        "User",
        back_populates="owned_lists",
    )

    tasks = relationship(
        "Task",
        back_populates="task_list",
        passive_deletes="all",
    )

    members = relationship(
        "ListMember",
        back_populates="task_list",
        passive_deletes="all",
    )

    notifications = relationship(
        "Notification",
        back_populates="task_list",
        passive_deletes="all",
    )

    activity_logs = relationship(
        "ActivityLog",
        back_populates="task_list",
        passive_deletes="all",
    )
