from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from backend.app.services.birthday_runner import (
    run_birthday_notifications,
)


def test_birthday_runner_commits_on_success():
    """
    Verifica que el ejecutor confirma la transacción
    y cierra la sesión cuando el proceso termina bien.
    """

    mock_db = MagicMock()
    test_date = date(2032, 6, 15)

    with (
        patch(
            "backend.app.services.birthday_runner.SessionLocal",
            return_value=mock_db,
        ),
        patch(
            "backend.app.services.birthday_runner."
            "process_birthday_notifications",
            return_value=4,
        ) as mock_process,
    ):
        result = run_birthday_notifications(
            today=test_date,
        )

    assert result == 4

    mock_process.assert_called_once_with(
        db=mock_db,
        today=test_date,
    )

    mock_db.commit.assert_called_once()
    mock_db.rollback.assert_not_called()
    mock_db.close.assert_called_once()


def test_birthday_runner_rolls_back_on_error():
    """
    Verifica que el ejecutor revierte la transacción
    y cierra la sesión cuando ocurre una excepción.
    """

    mock_db = MagicMock()
    test_date = date(2032, 6, 15)

    with (
        patch(
            "backend.app.services.birthday_runner.SessionLocal",
            return_value=mock_db,
        ),
        patch(
            "backend.app.services.birthday_runner."
            "process_birthday_notifications",
            side_effect=RuntimeError(
                "Error simulado de procesamiento"
            ),
        ),
    ):
        with pytest.raises(
            RuntimeError,
            match="Error simulado de procesamiento",
        ):
            run_birthday_notifications(
                today=test_date,
            )

    mock_db.commit.assert_not_called()
    mock_db.rollback.assert_called_once()
    mock_db.close.assert_called_once()