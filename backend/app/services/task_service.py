from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.list_member import ListMember
from backend.app.models.task import Task
from backend.app.models.task_list import TaskList


def get_accessible_list(
    db: Session,
    list_id: int,
    user_id: int,
    require_edit: bool = False,
) -> TaskList:
    """Comprueba si un usuario tiene acceso a una lista."""

    task_list = db.get(TaskList, list_id)

    if task_list is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lista no encontrada.",
        )

    if task_list.owner_id == user_id:
        return task_list

    if task_list.visibility != "shared":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lista no encontrada.",
        )

    membership = db.scalar(
        select(ListMember).where(
            ListMember.list_id == list_id,
            ListMember.user_id == user_id,
        )
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lista no encontrada.",
        )

    if require_edit and membership.role != "editor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para modificar esta lista.",
        )

    return task_list


def get_accessible_task(
    db: Session,
    task_id: int,
    user_id: int,
    require_edit: bool = False,
) -> Task:
    """Obtiene una tarea verificando los permisos."""

    task = db.get(Task, task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea no encontrada.",
        )

    get_accessible_list(
        db=db,
        list_id=task.list_id,
        user_id=user_id,
        require_edit=require_edit,
    )

    return task
