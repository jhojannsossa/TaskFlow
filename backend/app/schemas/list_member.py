from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ListMemberCreate(BaseModel):
    """Datos necesarios para añadir un colaborador."""

    user_id: int = Field(gt=0)
    role: Literal["editor", "viewer"] = "viewer"


class ListMemberUpdate(BaseModel):
    """Datos necesarios para modificar un rol."""

    role: Literal["editor", "viewer"]


class ListMemberResponse(BaseModel):
    """Datos que devuelve la API."""

    id: int
    list_id: int
    user_id: int
    role: Literal["editor", "viewer"]
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)
