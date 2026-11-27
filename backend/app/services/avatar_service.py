from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from backend.app.core.config import settings


ALLOWED_FORMATS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
}

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}


async def save_avatar(file: UploadFile) -> str:
    """Valida y guarda una fotografía de perfil."""

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se permiten imágenes JPG, PNG o WebP.",
        )

    max_size = settings.AVATAR_MAX_SIZE

    # Leer como máximo un byte adicional para detectar
    # archivos que superen el límite permitido.
    content = await file.read(max_size + 1)

    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="La fotografía no puede superar los 2 MB.",
        )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo está vacío.",
        )

    try:
        # Verificar que el archivo sea una imagen real.
        with Image.open(BytesIO(content)) as image:
            image.verify()

        # Abrir nuevamente para validar la decodificación.
        with Image.open(BytesIO(content)) as image:
            image_format = image.format

            if image_format not in ALLOWED_FORMATS:
                raise ValueError("Formato no permitido.")

            if image.width > 4096 or image.height > 4096:
                raise ValueError("La imagen supera las dimensiones permitidas.")

            image.load()

            # Normalizar la imagen para no conservar
            # metadatos innecesarios del archivo original.
            if image_format == "JPEG":
                normalized = image.convert("RGB")
            else:
                normalized = image.convert("RGBA")

            extension = ALLOWED_FORMATS[image_format]

            output = BytesIO()
            normalized.save(
                output,
                format=image_format,
            )

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo no es una imagen válida.",
        )

    if output.tell() > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="La imagen procesada supera los 2 MB.",
        )

    upload_dir: Path = settings.AVATAR_UPLOAD_DIR
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid4().hex}{extension}"
    destination = upload_dir / filename

    destination.write_bytes(output.getvalue())

    return filename


def delete_avatar_file(filename: str | None) -> None:
    """Elimina un archivo de avatar almacenado localmente."""

    if not filename:
        return

    # Solo se aceptan nombres de archivo, nunca rutas.
    safe_name = Path(filename).name

    if safe_name != filename:
        return

    if not safe_name.endswith((".jpg", ".png", ".webp")):
        return

    destination = settings.AVATAR_UPLOAD_DIR / safe_name

    if destination.is_file():
        destination.unlink()
