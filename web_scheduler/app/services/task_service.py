from zoneinfo import ZoneInfo

from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import TaskDefinition
from app.schemas.task import MIN_INTERVAL_SECONDS, TaskCreate, TaskUpdate
from app.services.exceptions import InvalidScheduleError

logger = get_logger(__name__)
settings = get_settings()


class TaskServiceError(Exception):
    pass


class TaskNotFoundError(TaskServiceError):
    pass


class TaskDuplicateNameError(TaskServiceError):
    pass


def _validate_task_schedule(task: TaskDefinition) -> None:
    if task.schedule_type == "cron":
        if not task.cron_expr:
            raise InvalidScheduleError("cron_expr is required for cron schedule")
        try:
            CronTrigger.from_crontab(task.cron_expr, timezone=ZoneInfo(task.timezone or settings.default_timezone))
        except ValueError as exc:
            raise InvalidScheduleError(f"Invalid cron expression: {task.cron_expr}") from exc
    elif task.schedule_type == "interval":
        if not task.interval_seconds or task.interval_seconds < MIN_INTERVAL_SECONDS:
            raise InvalidScheduleError(f"interval_seconds must be >= {MIN_INTERVAL_SECONDS}")


def create_task(db: Session, payload: TaskCreate) -> TaskDefinition:
    task = TaskDefinition(**payload.model_dump())
    _validate_task_schedule(task)

    db.add(task)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise TaskDuplicateNameError("Task name already exists") from exc

    db.refresh(task)

    if task.is_enabled and task.schedule_type in {"cron", "interval"}:
        from app.services.scheduler_service import update_task_schedule

        update_task_schedule(task)
        db.refresh(task)

    logger.info("Task created: id=%s, name=%s", task.id, task.name)
    return task


def list_tasks(
    db: Session,
    *,
    name: str | None = None,
    task_type: str | None = None,
    is_enabled: bool | None = None,
) -> list[TaskDefinition]:
    stmt = select(TaskDefinition)

    if name:
        stmt = stmt.where(TaskDefinition.name.ilike(f"%{name}%"))
    if task_type:
        stmt = stmt.where(TaskDefinition.task_type == task_type)
    if is_enabled is not None:
        stmt = stmt.where(TaskDefinition.is_enabled == is_enabled)

    stmt = stmt.order_by(TaskDefinition.created_at.desc())
    rows = db.execute(stmt).scalars().all()
    return list(rows)


def get_task(db: Session, task_id: int) -> TaskDefinition:
    task = db.get(TaskDefinition, task_id)
    if not task:
        raise TaskNotFoundError("Task not found")
    return task


def update_task(db: Session, task_id: int, payload: TaskUpdate) -> TaskDefinition:
    task = get_task(db, task_id)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(task, field, value)

    _validate_task_schedule(task)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise TaskDuplicateNameError("Task name already exists") from exc

    db.refresh(task)

    if task.is_enabled and task.schedule_type in {"cron", "interval"}:
        from app.services.scheduler_service import update_task_schedule

        update_task_schedule(task)
    else:
        from app.services.scheduler_service import remove_task

        remove_task(task.id)

    db.refresh(task)
    logger.info("Task updated: id=%s, name=%s", task.id, task.name)
    return task


def delete_task(db: Session, task_id: int) -> None:
    task = get_task(db, task_id)
    from app.services.scheduler_service import remove_task

    remove_task(task.id)
    db.delete(task)
    db.commit()
    logger.info("Task deleted: id=%s, name=%s", task.id, task.name)
