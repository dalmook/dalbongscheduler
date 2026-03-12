from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import TaskDefinition, TaskRun
from app.runners.html_runner import run_html_task
from app.runners.python_runner import run_python_task
from app.runners.sql_runner import run_sql_task
from app.services.artifact_service import create_artifact
from app.services.exceptions import (
    InvalidParamsJsonError,
    TaskExecutionError,
    TaskRunNotFoundError,
    UnsupportedTaskTypeError,
)
from app.services.task_service import TaskNotFoundError, get_task

logger = get_logger(__name__)


def _as_utc(dt: datetime) -> datetime:
    """Normalize DB datetime values for safe subtraction on SQLite.

    SQLite often returns naive datetimes even when timezone-aware columns are used.
    """

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def create_run_record(db: Session, task_id: int, trigger_type: str = "manual") -> TaskRun:
    run = TaskRun(task_id=task_id, trigger_type=trigger_type, status="queued")
    db.add(run)
    db.flush()
    return run


def mark_run_running(db: Session, run: TaskRun) -> TaskRun:
    run.status = "running"
    run.started_at = datetime.now(timezone.utc)
    db.flush()
    return run


def mark_run_success(db: Session, run: TaskRun, result_summary: str | None = None) -> TaskRun:
    finished_at = datetime.now(timezone.utc)
    run.status = "success"
    run.finished_at = finished_at
    run.result_summary = result_summary
    if run.started_at:
        run.duration_ms = int((finished_at - _as_utc(run.started_at)).total_seconds() * 1000)
    db.flush()
    return run


def mark_run_failed(db: Session, run: TaskRun, error_message: str) -> TaskRun:
    finished_at = datetime.now(timezone.utc)
    run.status = "failed"
    run.error_message = error_message
    run.finished_at = finished_at
    if run.started_at:
        run.duration_ms = int((finished_at - _as_utc(run.started_at)).total_seconds() * 1000)
    db.flush()
    return run


def _execute_by_task_type(task: TaskDefinition) -> dict[str, str | None]:
    if task.task_type == "python":
        return run_python_task(task.python_code, task.params_json)
    if task.task_type == "sql":
        return run_sql_task(task.sql_code, task.output_format)
    if task.task_type == "html":
        return run_html_task(task.html_template, task.params_json)

    raise UnsupportedTaskTypeError(f"Unsupported task type: {task.task_type}")


def run_task(db: Session, task_id: int, trigger_type: str = "manual") -> TaskRun:
    try:
        task = get_task(db, task_id)
    except TaskNotFoundError:
        raise

    run = create_run_record(db, task_id=task.id, trigger_type=trigger_type)
    db.commit()

    try:
        mark_run_running(db, run)
        db.commit()

        result = _execute_by_task_type(task)

        create_artifact(
            db,
            task_id=task.id,
            run_id=run.id,
            artifact_type=(result.get("artifact_type") or "text"),
            content_text=result.get("content_text"),
            content_html=result.get("content_html"),
            content_json=result.get("content_json"),
        )

        mark_run_success(db, run, result.get("summary"))
        task.last_run_status = "success"
        task.last_run_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
        logger.info("Task run success: task_id=%s run_id=%s", task.id, run.id)
        return run

    except (TaskExecutionError, InvalidParamsJsonError, UnsupportedTaskTypeError) as exc:
        mark_run_failed(db, run, str(exc))
        task.last_run_status = "failed"
        task.last_run_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
        logger.exception("Task run failed: task_id=%s run_id=%s", task.id, run.id)
        raise
    except Exception as exc:
        mark_run_failed(db, run, str(exc))
        task.last_run_status = "failed"
        task.last_run_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
        logger.exception("Unexpected execution error: task_id=%s run_id=%s", task.id, run.id)
        raise TaskExecutionError(str(exc)) from exc


def list_runs(
    db: Session,
    *,
    task_id: int | None = None,
    status: str | None = None,
    trigger_type: str | None = None,
) -> list[TaskRun]:
    stmt = select(TaskRun)
    if task_id is not None:
        stmt = stmt.where(TaskRun.task_id == task_id)
    if status:
        stmt = stmt.where(TaskRun.status == status)
    if trigger_type:
        stmt = stmt.where(TaskRun.trigger_type == trigger_type)

    return list(db.execute(stmt.order_by(TaskRun.created_at.desc())).scalars().all())


def get_run(db: Session, run_id: int) -> TaskRun:
    run = db.get(TaskRun, run_id)
    if not run:
        raise TaskRunNotFoundError("Run not found")
    return run
