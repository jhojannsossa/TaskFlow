from datetime import datetime, timedelta, timezone

from sqlalchemy import func, and_, or_, select
from sqlalchemy.orm import Session

from backend.app.models.task import Task
from backend.app.models.task_list import TaskList
from backend.app.models.list_member import ListMember
from backend.app.models.activity import ActivityLog


def get_accessible_list_ids(db: Session, user_id: int) -> list[int]:
    """Obtiene las listas propias o compartidas con el usuario."""

    statement = (
        select(TaskList.id)
        .outerjoin(
            ListMember,
            ListMember.list_id == TaskList.id,
        )
        .where(
            or_(
                TaskList.owner_id == user_id,
                and_(
                    ListMember.user_id == user_id,
                    TaskList.visibility == "shared",
                ),
            )
        )
        .distinct()
    )

    return list(db.scalars(statement).all())


def get_tasks_by_status(db: Session, user_id: int) -> dict:
    """Cuenta las tareas accesibles agrupadas por estado."""

    list_ids = get_accessible_list_ids(db, user_id)

    result = {
        "todo": 0,
        "in_progress": 0,
        "done": 0,
    }

    if not list_ids:
        return result

    statement = (
        select(Task.status, func.count(Task.id))
        .where(Task.list_id.in_(list_ids))
        .group_by(Task.status)
    )

    for status, count in db.execute(statement):
        result[status] = count

    return result


def get_tasks_by_list(db: Session, user_id: int) -> list[dict]:
    """Cuenta las tareas de cada lista accesible."""

    list_ids = get_accessible_list_ids(db, user_id)

    if not list_ids:
        return []

    statement = (
        select(
            TaskList.id,
            TaskList.name,
            func.count(Task.id),
        )
        .outerjoin(Task, Task.list_id == TaskList.id)
        .where(TaskList.id.in_(list_ids))
        .group_by(TaskList.id, TaskList.name)
        .order_by(TaskList.name, TaskList.id)
    )

    return [
        {
            "list_id": list_id,
            "list_name": name,
            "total_tasks": total,
        }
        for list_id, name, total in db.execute(statement)
    ]


def get_weekly_statistics(
    db: Session,
    user_id: int,
    weeks: int = 4,
) -> list[dict]:
    """Calcula tareas creadas y completadas por semana."""

    if not 1 <= weeks <= 52:
        raise ValueError("weeks debe estar entre 1 y 52")

    list_ids = get_accessible_list_ids(db, user_id)

    today = datetime.now(timezone.utc).date()
    current_monday = today - timedelta(days=today.weekday())

    results = []

    for offset in range(weeks - 1, -1, -1):
        week_start = current_monday - timedelta(weeks=offset)
        week_end = week_start + timedelta(days=7)

        start_dt = datetime.combine(
            week_start,
            datetime.min.time(),
            tzinfo=timezone.utc,
        )
        end_dt = datetime.combine(
            week_end,
            datetime.min.time(),
            tzinfo=timezone.utc,
        )

        created = 0
        completed = 0

        if list_ids:
            created = db.scalar(
                select(func.count(Task.id)).where(
                    Task.list_id.in_(list_ids),
                    Task.created_at >= start_dt,
                    Task.created_at < end_dt,
                )
            ) or 0

            completed = db.scalar(
                select(func.count(Task.id)).where(
                    Task.list_id.in_(list_ids),
                    Task.completed_at >= start_dt,
                    Task.completed_at < end_dt,
                )
            ) or 0

        results.append(
            {
                "week_start": week_start.isoformat(),
                "created": created,
                "completed": completed,
            }
        )

    return results


def get_recent_activity(
    db: Session,
    user_id: int,
    limit: int = 10,
) -> list[dict]:
    """Obtiene actividad reciente visible para el usuario."""

    if not 1 <= limit <= 100:
        raise ValueError("limit debe estar entre 1 y 100")

    list_ids = get_accessible_list_ids(db, user_id)

    conditions = [
        and_(
            ActivityLog.user_id == user_id,
            ActivityLog.list_id.is_(None),
        )
    ]

    if list_ids:
        conditions.append(
            ActivityLog.list_id.in_(list_ids)
        )

    statement = (
        select(ActivityLog)
        .where(or_(*conditions))
        .order_by(
            ActivityLog.created_at.desc(),
            ActivityLog.id.desc(),
        )
        .limit(limit)
    )

    activities = db.scalars(statement).all()

    return [
        {
            "id": activity.id,
            "user_id": activity.user_id,
            "task_id": activity.task_id,
            "list_id": activity.list_id,
            "action": activity.action,
            "details": activity.details,
            "created_at": activity.created_at.isoformat(),
        }
        for activity in activities
    ]
