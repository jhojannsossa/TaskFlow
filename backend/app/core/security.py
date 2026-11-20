from datetime import datetime, timedelta, timezone

import jwt

from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from backend.app.core.config import settings


# Configuramos Argon2 para proteger las contraseñas.
password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Convierte una contraseña en un hash seguro."""

    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """Comprueba si una contraseña coincide con su hash."""

    return password_hash.verify(
        plain_password,
        hashed_password,
    )


def create_access_token(user_id: int) -> str:
    """Genera un JWT para un usuario autenticado."""

    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "exp": expires_at,
        "iat": datetime.now(timezone.utc),
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_access_token(token: str) -> int | None:
    """Verifica el JWT y devuelve el ID del usuario."""

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        user_id = payload.get("sub")

        if not isinstance(user_id, str):
            return None

        if not user_id.isdecimal():
            return None

        parsed_user_id = int(user_id)

        if parsed_user_id <= 0:
            return None

        return parsed_user_id

    except InvalidTokenError:
        return None
