from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.database.connection import get_db
from backend.app.core.dependencies import get_current_user
from backend.app.models.user import User

from backend.app.services.statistics_service import (
    get_tasks_by_status,
    get_tasks_by_list,
    get_weekly_statistics,
    get_recent_activity,
)


router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"],
)


@router.get("/tasks-by-status")
def tasks_by_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve el número de tareas por estado."""

    return get_tasks_by_status(
        db=db,
        user_id=current_user.id,
    )


@router.get("/tasks-by-list")
def tasks_by_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve el número de tareas por lista."""

    return get_tasks_by_list(
        db=db,
        user_id=current_user.id,
    )


@router.get("/weekly")
def weekly_statistics(
    weeks: int = Query(default=4, ge=1, le=52),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve las estadísticas de las últimas semanas."""

    return get_weekly_statistics(
        db=db,
        user_id=current_user.id,
        weeks=weeks,
    )


@router.get("/recent-activity")
def recent_activity(
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve los últimos registros de actividad."""

    return get_recent_activity(
        db=db,
        user_id=current_user.id,
        limit=limit,
    )
