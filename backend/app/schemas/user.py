from datetime import date, datetime

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
    """Información pública básica del usuario."""

    id: int
    name: str
    email: EmailStr
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserProfileResponse(UserResponse):
    """Información privada del perfil autenticado."""

    avatar_url: str | None = None
    job_title: str | None = None
    birth_date: date | None = None
    share_birthday: bool = False



class UserLogin(BaseModel):
    """Credenciales para iniciar sesión mediante JSON."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Respuesta de autenticación con JWT."""

    access_token: str
    token_type: str = "bearer"

class UserUpdate(BaseModel):
    """Datos que el usuario puede modificar en su perfil."""

    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    email: EmailStr | None = None

    job_title: str | None = Field(
        default=None,
        max_length=100,
    )

    birth_date: date | None = None

    share_birthday: bool | None = None