from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_current_user
from backend.app.database.connection import get_db
from backend.app.models.user import User
from backend.app.schemas.user import UserResponse


router = APIRouter(
    prefix="/api/users",
    tags=["Users"],
)


@router.get(
    "/by-email",
    response_model=UserResponse,
)
def get_user_by_email(
    email: EmailStr,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Busca un usuario activo por su correo electrónico."""

    normalized_email = str(email).strip().lower()

    user = db.scalar(
        select(User).where(
            User.email == normalized_email,
            User.is_active.is_(True),
        )
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado.",
        )

    return user