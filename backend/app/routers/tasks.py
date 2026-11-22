from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_current_user
from backend.app.database.connection import get_db
from backend.app.models.list_member import ListMember
from backend.app.models.task import Task
from backend.app.models.activity import ActivityLog
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
    validate_task_assignee,
)

from backend.app.services.notification_service import create_notification

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

    validate_task_assignee(
        db=db,
        list_id=task_data.list_id,
        assigned_to=task_data.assigned_to,
    )

    task = Task(
        **task_data.model_dump(),
        created_by=current_user.id,
    )

    if task.status == "done":
        task.completed_at = datetime.now(timezone.utc)

    db.add(task)
    db.flush()

    db.add(
        ActivityLog(
            user_id=current_user.id,
            task_id=task.id,
            list_id=task.list_id,
            action="task_created",
            details={
                "title": task.title,
                "status": task.status,
            },
        )
    )

    if task.assigned_to is not None and task.assigned_to != current_user.id:
        create_notification(
            db=db,
            user_id=task.assigned_to,
            notification_type="assignment",
            message=f"Te han asignado la tarea: {task.title}",
            task_id=task.id,
            list_id=task.list_id,
        )

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
    """Actualiza una tarea y genera notificaciones."""

    task = get_accessible_task(
        db,
        task_id,
        current_user.id,
        require_edit=True,
    )

    changes = task_data.model_dump(exclude_unset=True)

    if "assigned_to" in changes:
        validate_task_assignee(
            db=db,
            list_id=task.list_id,
            assigned_to=changes["assigned_to"],
        )

    previous_status = task.status
    previous_assignee = task.assigned_to

    if "status" in changes:
        new_status = changes["status"]

        if new_status == "done" and task.status != "done":
            task.completed_at = datetime.now(timezone.utc)

        elif new_status != "done":
            task.completed_at = None

    for field, value in changes.items():
        setattr(task, field, value)

    # Notificar si cambia el responsable.
    if (
        task.assigned_to is not None
        and task.assigned_to != previous_assignee
        and task.assigned_to != current_user.id
    ):
        create_notification(
            db=db,
            user_id=task.assigned_to,
            notification_type="assignment",
            message=f"Te han asignado la tarea: {task.title}",
            task_id=task.id,
            list_id=task.list_id,
        )

    # Notificar si cambia el estado.
    if (
        task.status != previous_status
        and task.assigned_to is not None
        and task.assigned_to != current_user.id
    ):
        create_notification(
            db=db,
            user_id=task.assigned_to,
            notification_type="status_change",
            message=(
                f"La tarea '{task.title}' cambió "
                f"de '{previous_status}' a '{task.status}'."
            ),
            task_id=task.id,
            list_id=task.list_id,
        )

    # Registrar los cambios realizados en la tarea.
    if changes:
        activity_action = (
            "task_status_changed"
            if task.status != previous_status
            else "task_updated"
        )

        db.add(
            ActivityLog(
                user_id=current_user.id,
                task_id=task.id,
                list_id=task.list_id,
                action=activity_action,
                details={
                    "title": task.title,
                    "changed_fields": list(changes.keys()),
                    "previous_status": previous_status,
                    "new_status": task.status,
                },
            )
        )

    # Guardar la tarea, las notificaciones y la actividad.
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

    # Guardar los datos antes de eliminar la tarea.
    deleted_task_id = task.id
    deleted_task_title = task.title
    deleted_list_id = task.list_id

    # Registrar la eliminación.
    # task_id=None evita mantener una referencia
    # a una tarea que dejará de existir.
    db.add(
        ActivityLog(
            user_id=current_user.id,
            task_id=None,
            list_id=deleted_list_id,
            action="task_deleted",
            details={
                "deleted_task_id": deleted_task_id,
                "title": deleted_task_title,
            },
        )
    )

    # Eliminar la tarea y guardar ambas operaciones.
    db.delete(task)
    db.commit()