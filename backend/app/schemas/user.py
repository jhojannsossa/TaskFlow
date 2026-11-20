from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Datos necesarios para registrar un usuario."""

    name: str = Field(
        min_length=2,
        max_length=100,
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
    )


class UserResponse(BaseModel):
    """Información pública que devuelve la API."""

    id: int
    name: str
    email: EmailStr
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    """Credenciales para iniciar sesión mediante JSON."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Respuesta de autenticación con JWT."""

    access_token: str
    token_type: str = "bearer"