"""add birthday notification delivery fields

Revision ID: 65741e18de19
Revises: 10f35301e268
Create Date: 2026-11-27 14:54:47.303194

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Identificadores de la migración.
revision: str = "65741e18de19"

down_revision: Union[str, Sequence[str], None] = (
    "10f35301e268"
)

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Añade los campos necesarios para registrar
    notificaciones de cumpleaños y evitar duplicados.
    """

    # Usuario cuyo cumpleaños genera la notificación.
    op.add_column(
        "notifications",
        sa.Column(
            "birthday_user_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    # Año correspondiente a la felicitación.
    op.add_column(
        "notifications",
        sa.Column(
            "birthday_year",
            sa.Integer(),
            nullable=True,
        ),
    )

    # Clave foránea hacia la tabla de usuarios.
    op.create_foreign_key(
        "fk_notifications_birthday_user_id",
        "notifications",
        "users",
        ["birthday_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Impide duplicar una felicitación para el mismo
    # destinatario, tipo, usuario y año.
    op.create_index(
        "uq_notifications_birthday_delivery",
        "notifications",
        [
            "user_id",
            "type",
            "birthday_user_id",
            "birthday_year",
        ],
        unique=True,
    )


def downgrade() -> None:
    """
    Revierte exclusivamente los cambios
    introducidos por esta migración.
    """

    # Eliminar el índice único.
    op.drop_index(
        "uq_notifications_birthday_delivery",
        table_name="notifications",
    )

    # Eliminar la clave foránea.
    op.drop_constraint(
        "fk_notifications_birthday_user_id",
        "notifications",
        type_="foreignkey",
    )

    # Eliminar las columnas añadidas.
    op.drop_column(
        "notifications",
        "birthday_year",
    )

    op.drop_column(
        "notifications",
        "birthday_user_id",
    )
