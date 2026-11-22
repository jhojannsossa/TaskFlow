from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_current_user
from backend.app.database.connection import get_db
from backend.app.models.list_member import ListMember
from backend.app.models.task_list import TaskList
from backend.app.models.activity import ActivityLog
from backend.app.models.user import User
from backend.app.schemas.task_list import (
    TaskListCreate,
    TaskListUpdate,
    TaskListResponse,
)
from backend.app.schemas.list_member import (
    ListMemberCreate,
    ListMemberUpdate,
    ListMemberResponse,
)


router = APIRouter(
    prefix="/api/lists",
    tags=["Lists"],
)


@router.post(
    "",
    response_model=TaskListResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_list(
    list_data: TaskListCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crea una lista cuyo propietario es el usuario autenticado."""

    new_list = TaskList(
        **list_data.model_dump(),
        owner_id=current_user.id,
    )

    # Crear la lista y obtener su identificador.
    db.add(new_list)
    db.flush()

    # Registrar la creación de la lista.
    db.add(
        ActivityLog(
            user_id=current_user.id,
            list_id=new_list.id,
            action="list_created",
            details={
                "name": new_list.name,
                "visibility": new_list.visibility,
            },
        )
    )

    # Guardar la lista y su actividad en una sola transacción.
    db.commit()
    db.refresh(new_list)

    return new_list



@router.get(
    "",
    response_model=list[TaskListResponse],
)
def get_lists(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve las listas propias y las compartidas con el usuario."""

    query = (
        select(TaskList)
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

        .distinct()
        .order_by(TaskList.created_at.desc(), TaskList.id.desc())
    )

    return db.scalars(query).all()


@router.get(
    "/{list_id}",
    response_model=TaskListResponse,
)
def get_list(
    list_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Consulta una lista si el usuario tiene acceso."""

    task_list = db.get(TaskList, list_id)

    if task_list is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lista no encontrada",
        )

    if task_list.owner_id == current_user.id:
        return task_list

    if task_list.visibility != "shared":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lista no encontrada",
        )

    membership = db.scalar(
        select(ListMember).where(
            ListMember.list_id == list_id,
            ListMember.user_id == current_user.id,
        )
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lista no encontrada",
        )

    return task_list

@router.patch(
    "/{list_id}",
    response_model=TaskListResponse,
)
def update_list(
    list_id: int,
    list_data: TaskListUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permite al propietario modificar su lista."""

    task_list = db.get(TaskList, list_id)

    if task_list is None or task_list.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lista no encontrada",
        )

    changes = list_data.model_dump(exclude_unset=True)

    if changes.get("name") is None and "name" in changes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="El nombre no puede ser nulo",
        )

    if changes.get("visibility") is None and "visibility" in changes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La visibilidad no puede ser nula",
        )

    # Guardar los valores anteriores para el historial.
    previous_values = {
        field: getattr(task_list, field)
        for field in changes
    }

    # Aplicar los cambios a la lista.
    for field, value in changes.items():
        setattr(task_list, field, value)

    # Registrar únicamente los campos que realmente cambiaron.
    changed_fields = {
        field: {
            "previous": previous_values[field],
            "new": value,
        }
        for field, value in changes.items()
        if previous_values[field] != value
    }

    if changed_fields:
        db.add(
            ActivityLog(
                user_id=current_user.id,
                list_id=task_list.id,
                action="list_updated",
                details={
                    "name": task_list.name,
                    "changes": changed_fields,
                },
            )
        )

    # Guardar la actualización y la actividad juntas.
    db.commit()
    db.refresh(task_list)

    return task_list



@router.delete(
    "/{list_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_list(
    list_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permite al propietario eliminar su lista."""

    task_list = db.get(TaskList, list_id)

    if task_list is None or task_list.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lista no encontrada",
        )

    # Guardar los datos antes de eliminar la lista.
    deleted_list_id = task_list.id
    deleted_list_name = task_list.name
    deleted_visibility = task_list.visibility

    # Registrar la eliminación sin mantener una referencia
    # a la lista que dejará de existir.
    db.add(
        ActivityLog(
            user_id=current_user.id,
            list_id=None,
            action="list_deleted",
            details={
                "deleted_list_id": deleted_list_id,
                "name": deleted_list_name,
                "visibility": deleted_visibility,
            },
        )
    )

    # Eliminar la lista y guardar el evento.
    db.delete(task_list)
    db.commit()


@router.post(
    "/{list_id}/members",
    response_model=ListMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_list_member(
    list_id: int,
    member_data: ListMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permite al propietario añadir colaboradores."""

    task_list = db.get(TaskList, list_id)

    if task_list is None or task_list.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lista no encontrada",
        )

    if task_list.visibility != "shared":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La lista debe estar compartida",
        )

    if member_data.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El propietario no puede añadirse como colaborador",
        )

    target_user = db.get(User, member_data.user_id)

    if target_user is None or not target_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado o inactivo",
        )

    existing_member = db.scalar(
        select(ListMember).where(
            ListMember.list_id == list_id,
            ListMember.user_id == member_data.user_id,
        )
    )

    if existing_member is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El usuario ya pertenece a esta lista",
        )

    new_member = ListMember(
        list_id=list_id,
        user_id=member_data.user_id,
        role=member_data.role,
    )

    # Crear el nuevo colaborador.
    db.add(new_member)
    db.flush()

    # Registrar la incorporación del colaborador.
    db.add(
        ActivityLog(
            user_id=current_user.id,
            list_id=list_id,
            action="list_member_added",
            details={
                "member_user_id": new_member.user_id,
                "role": new_member.role,
                "list_name": task_list.name,
            },
        )
    )

    # Guardar ambas operaciones en una sola transacción.
    db.commit()
    db.refresh(new_member)

    return new_member

@router.get(
    "/{list_id}/members",
    response_model=list[ListMemberResponse],
)
def get_list_members(
    list_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Consulta los colaboradores de una lista accesible."""

    task_list = db.get(TaskList, list_id)

    if task_list is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lista no encontrada",
        )

    # El propietario puede consultar su lista.
    # Los colaboradores solo pueden acceder si es compartida.
    if task_list.owner_id != current_user.id:

        if task_list.visibility != "shared":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lista no encontrada",
            )

        membership = db.scalar(
            select(ListMember).where(
                ListMember.list_id == list_id,
                ListMember.user_id == current_user.id,
            )
        )

        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Lista no encontrada",
            )

    members = db.scalars(
        select(ListMember)
        .where(ListMember.list_id == list_id)
        .order_by(ListMember.id)
    ).all()

    return members

@router.patch(
    "/{list_id}/members/{user_id}",
    response_model=ListMemberResponse,
)
def update_list_member(
    list_id: int,
    user_id: int,
    member_data: ListMemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permite al propietario cambiar el rol de un colaborador."""

    task_list = db.get(TaskList, list_id)

    if task_list is None or task_list.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lista no encontrada",
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
            detail="Colaborador no encontrado",
        )

       # Guardar el rol anterior.
    previous_role = membership.role
    new_role = member_data.role

    # Actualizar el rol del colaborador.
    membership.role = new_role

    # Registrar la actividad solo si el rol cambió.
    if previous_role != new_role:
        db.add(
            ActivityLog(
                user_id=current_user.id,
                list_id=list_id,
                action="list_member_role_changed",
                details={
                    "member_user_id": membership.user_id,
                    "previous_role": previous_role,
                    "new_role": new_role,
                    "list_name": task_list.name,
                },
            )
        )

    # Guardar ambos cambios en una sola transacción.
    db.commit()
    db.refresh(membership)

    return membership


@router.delete(
    "/{list_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_list_member(
    list_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permite al propietario eliminar un colaborador."""

    task_list = db.get(TaskList, list_id)

    if task_list is None or task_list.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lista no encontrada",
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
            detail="Colaborador no encontrado",
        )

    # Guardar los datos del colaborador antes de eliminarlo.
    removed_user_id = membership.user_id
    removed_role = membership.role

    # Registrar la eliminación del colaborador.
    db.add(
        ActivityLog(
            user_id=current_user.id,
            list_id=list_id,
            action="list_member_removed",
            details={
                "member_user_id": removed_user_id,
                "previous_role": removed_role,
                "list_name": task_list.name,
            },
        )
    )

    # Eliminar al colaborador y guardar la actividad.
    db.delete(membership)
    db.commit()