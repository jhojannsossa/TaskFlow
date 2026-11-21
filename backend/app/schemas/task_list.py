from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ListVisibility = Literal["private", "shared"]


class TaskListCreate(BaseModel):
    """Datos necesarios para crear una lista."""

    name: str = Field(
        min_length=1,
        max_length=100,
    )

    description: str | None = None

    visibility: ListVisibility = "private"


class TaskListUpdate(BaseModel):
    """Datos que podrán modificarse posteriormente."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    description: str | None = None

    visibility: ListVisibility | None = None


class TaskListResponse(BaseModel):
    """Información que devolverá la API."""

    id: int
    owner_id: int
    name: str
    description: str | None
    visibility: ListVisibility
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)