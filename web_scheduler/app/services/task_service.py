from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import TaskDefinition
from app.schemas.task import TaskCreate, TaskUpdate

logger = get_logger(__name__)


class TaskServiceError(Exception):
    pass


class TaskNotFoundError(TaskServiceError):
    pass


class TaskDuplicateNameError(TaskServiceError):
    pass


def create_task(db: Session, payload: TaskCreate) -> TaskDefinition:
    task = TaskDefinition(**payload.model_dump())
    db.add(task)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise TaskDuplicateNameError("Task name already exists") from exc

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

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise TaskDuplicateNameError("Task name already exists") from exc

    db.refresh(task)
    logger.info("Task updated: id=%s, name=%s", task.id, task.name)
    return task


def delete_task(db: Session, task_id: int) -> None:
    task = get_task(db, task_id)
    db.delete(task)
    db.commit()
    logger.info("Task deleted: id=%s, name=%s", task.id, task.name)
