from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_current_user
from backend.app.database.connection import get_db
from backend.app.models.list_member import ListMember
from backend.app.models.task import Task
from backend.app.models.task_list import TaskList
from backend.app.models.user import User
from backend.app.schemas.task import (
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)
from backend.app.services.task_service import (
    get_accessible_list,
    get_accessible_task,
)


router = APIRouter(
    prefix="/api/tasks",
    tags=["Tasks"],
)


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crea una tarea en una lista autorizada."""

    get_accessible_list(
        db,
        task_data.list_id,
        current_user.id,
        require_edit=True,
    )

    task = Task(
        **task_data.model_dump(),
        created_by=current_user.id,
    )

    if task.status == "done":
        task.completed_at = datetime.now(timezone.utc)

    db.add(task)
    db.commit()
    db.refresh(task)

    return task


@router.get("", response_model=list[TaskResponse])
def list_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista las tareas accesibles para el usuario."""

    accessible_lists = (
        select(TaskList.id)
        .outerjoin(
            ListMember,
            ListMember.list_id == TaskList.id,
        )
       .where(
            or_(
                TaskList.owner_id == current_user.id,
                (
                    (ListMember.user_id == current_user.id)
                    & (TaskList.visibility == "shared")
                ),
            )
        )
    )

    tasks = db.scalars(
        select(Task)
        .where(Task.list_id.in_(accessible_lists))
        .order_by(Task.created_at.desc(), Task.id.desc())
    ).all()

    return tasks


@router.get("/{task_id}", response_model=TaskResponse)
def read_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Consulta una tarea autorizada."""

    return get_accessible_task(
        db,
        task_id,
        current_user.id,
    )


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualiza una tarea autorizada."""

    task = get_accessible_task(
        db,
        task_id,
        current_user.id,
        require_edit=True,
    )

    changes = task_data.model_dump(exclude_unset=True)

    if "status" in changes:
        new_status = changes["status"]

        if new_status == "done" and task.status != "done":
            task.completed_at = datetime.now(timezone.utc)

        elif new_status != "done":
            task.completed_at = None

    for field, value in changes.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)

    return task


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Elimina una tarea autorizada."""

    task = get_accessible_task(
        db,
        task_id,
        current_user.id,
        require_edit=True,
    )

    db.delete(task)
    db.commit()
