import logging
from datetime import date

from backend.app.database.connection import SessionLocal
from backend.app.services.birthday_service import (
    process_birthday_notifications,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


def run_birthday_notifications(
    today: date | None = None,
) -> int:
    """
    Ejecuta el procesamiento de cumpleaños
    dentro de una transacción de PostgreSQL.

    Confirma los cambios cuando termina
    correctamente.

    Revierte los cambios si ocurre un error.

    Devuelve el número de notificaciones creadas.
    """

    db = SessionLocal()

    try:
        logger.info(
            "Iniciando procesamiento de cumpleaños."
        )

        created_count = process_birthday_notifications(
            db=db,
            today=today,
        )

        # Confirmar las notificaciones.
        # También libera el bloqueo transaccional.
        db.commit()

        logger.info(
            "Procesamiento completado. "
            "Notificaciones creadas: %s",
            created_count,
        )

        return created_count

    except Exception:
        # Revertir los cambios y liberar el bloqueo.
        db.rollback()

        logger.exception(
            "Error durante el procesamiento "
            "de cumpleaños."
        )

        raise

    finally:
        db.close()


if __name__ == "__main__":
    run_birthday_notifications()