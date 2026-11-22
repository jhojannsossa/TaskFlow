from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TaskStatus = Literal["todo", "in_progress", "done"]
TaskPriority = Literal["low", "medium", "high", "urgent"]


class TaskCreate(BaseModel):
    """Datos necesarios para crear una tarea."""

    list_id: int = Field(gt=0)

    title: str = Field(
        min_length=1,
        max_length=200,
    )

    description: str | None = None

    assigned_to: int | None = Field(
        default=None,
        gt=0,
)
    status: TaskStatus = "todo"

    priority: TaskPriority = "medium"

    due_date: datetime | None = None


class TaskUpdate(BaseModel):
    """Datos que se pueden modificar de una tarea."""

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

    description: str | None = None

    assigned_to: int | None = Field(
        default=None,
        gt=0,
    )

    status: TaskStatus | None = None

    priority: TaskPriority | None = None

    due_date: datetime | None = None


class TaskResponse(BaseModel):
    """Datos públicos que devuelve la API."""

    id: int

    list_id: int

    created_by: int

    assigned_to: int | None

    title: str

    description: str | None

    status: TaskStatus

    priority: TaskPriority

    due_date: datetime | None

    completed_at: datetime | None

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
