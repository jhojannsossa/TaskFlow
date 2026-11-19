from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base


class ListMember(Base):
    __tablename__ = "list_members"

    __table_args__ = (
        UniqueConstraint(
            "list_id",
            "user_id",
            name="uq_list_members_list_user",
        ),
        CheckConstraint(
            "role IN ('editor', 'viewer')",
            name="ck_list_members_role",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        Identity(),
        primary_key=True,
    )

    list_id: Mapped[int] = mapped_column(
        ForeignKey("task_lists.id"),
        nullable=False,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    # ORM relationships
    task_list = relationship(
        "TaskList",
        back_populates="members",
    )

    user = relationship(
        "User",
        back_populates="memberships",
    )
