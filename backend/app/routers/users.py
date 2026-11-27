from datetime import date

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_current_user
from backend.app.database.connection import get_db
from backend.app.models.user import User
from backend.app.schemas.user import (
    UserResponse,
    UserProfileResponse,
    UserUpdate,
)
from backend.app.services.avatar_service import (
    save_avatar,
    delete_avatar_file,
)


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


@router.patch(
    "/me",
    response_model=UserProfileResponse,
)
def update_my_profile(
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualiza el perfil del usuario autenticado."""

    changes = user_data.model_dump(exclude_unset=True)

    if "name" in changes:
        name = changes["name"]

        if name is None or len(name.strip()) < 2:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El nombre debe tener al menos 2 caracteres.",
            )

        current_user.name = name.strip()

    if "email" in changes:
        email = changes["email"]

        if email is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El correo electrónico es obligatorio.",
            )

        normalized_email = str(email).strip().lower()

        existing_user = db.scalar(
            select(User).where(
                User.email == normalized_email,
                User.id != current_user.id,
            )
        )

        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El correo electrónico ya está registrado.",
            )

        current_user.email = normalized_email

    if "job_title" in changes:
        job_title = changes["job_title"]

        current_user.job_title = (
            job_title.strip() if job_title else None
        )

    if "birth_date" in changes:
        birth_date = changes["birth_date"]

        if birth_date is not None and birth_date > date.today():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La fecha de nacimiento no puede ser futura.",
            )

        current_user.birth_date = birth_date

    if "share_birthday" in changes:
        share_birthday = changes["share_birthday"]

        if share_birthday is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Debes indicar si deseas compartir tu cumpleaños.",
            )

        current_user.share_birthday = share_birthday

    try:
        db.commit()
        db.refresh(current_user)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo electrónico ya está registrado.",
        )

    return current_user

@router.post(
    "/me/avatar",
    response_model=UserProfileResponse,
)
async def upload_my_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sube o reemplaza la fotografía del usuario autenticado."""

    old_avatar = current_user.avatar_url

    # Validar y guardar la nueva imagen.
    filename = await save_avatar(file)

    current_user.avatar_url = f"/uploads/avatars/{filename}"

    try:
        db.commit()
        db.refresh(current_user)

    except Exception:
        db.rollback()
        delete_avatar_file(filename)
        raise

    # Eliminar la imagen anterior después de guardar
    # correctamente la nueva referencia.
    if old_avatar:
        old_filename = old_avatar.rsplit("/", 1)[-1]
        if old_filename != filename:
            delete_avatar_file(old_filename)

    return current_user

@router.delete(
    "/me/avatar",
    response_model=UserProfileResponse,
)
def remove_my_avatar(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Elimina la fotografía del usuario autenticado."""

    old_avatar = current_user.avatar_url

    current_user.avatar_url = None

    try:
        db.commit()
        db.refresh(current_user)

    except Exception:
        db.rollback()
        raise

    if old_avatar:
        old_filename = old_avatar.rsplit("/", 1)[-1]
        delete_avatar_file(old_filename)

    return current_user