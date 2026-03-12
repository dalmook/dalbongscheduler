from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import TaskDefinition
from app.db.session import SessionLocal
from app.services.execution_service import run_task
from app.services.exceptions import InvalidScheduleError, SchedulerRegistrationError

logger = get_logger(__name__)
_settings = get_settings()
_scheduler = BackgroundScheduler(timezone=_settings.default_timezone)


def _job_id(task_id: int) -> str:
    return f"task:{task_id}"


def _trigger_for_task(task: TaskDefinition):
    tz = ZoneInfo(task.timezone or _settings.default_timezone)

    if task.schedule_type == "cron":
        if not task.cron_expr:
            raise InvalidScheduleError("cron_expr is required for cron schedule")
        try:
            return CronTrigger.from_crontab(task.cron_expr, timezone=tz)
        except ValueError as exc:
            raise InvalidScheduleError(f"Invalid cron expression: {task.cron_expr}") from exc

    if task.schedule_type == "interval":
        if not task.interval_seconds or task.interval_seconds < 10:
            raise InvalidScheduleError("interval_seconds must be >= 10 for interval schedule")
        return IntervalTrigger(seconds=task.interval_seconds, timezone=tz)

    raise InvalidScheduleError(f"Unsupported schedule_type for scheduler registration: {task.schedule_type}")


def init_scheduler() -> None:
    """Initialize scheduler resources for runtime registration."""

    logger.info("Scheduler initialized")


def start_scheduler() -> None:
    if not _scheduler.running:
        _scheduler.start()
        logger.info("Scheduler started")


def shutdown_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler shutdown complete")


def _run_task_job(task_id: int) -> None:
    """Scheduled job entrypoint. Must never raise uncaught exceptions."""

    logger.info("Auto run triggered: task_id=%s", task_id)
    with SessionLocal() as db:
        try:
            run = run_task(db, task_id=task_id, trigger_type="scheduled")
            job = get_job_for_task(task_id)
            db_task = db.get(TaskDefinition, task_id)
            if db_task:
                db_task.next_run_at = job.next_run_time if job else None
                db.commit()
            logger.info("Auto run success: task_id=%s run_id=%s status=%s", task_id, run.id, run.status)
        except Exception as exc:
            logger.exception("Auto run failed: task_id=%s error=%s", task_id, exc)


def compute_next_run_at(task: TaskDefinition) -> datetime | None:
    job = _scheduler.get_job(_job_id(task.id))
    if job and job.next_run_time:
        return job.next_run_time

    try:
        trigger = _trigger_for_task(task)
    except InvalidScheduleError:
        return None
    now = datetime.now(ZoneInfo(task.timezone or _settings.default_timezone))
    return trigger.get_next_fire_time(previous_fire_time=None, now=now)


def register_task(task: TaskDefinition) -> None:
    """Register/update a scheduler job for a single task."""

    if not task.is_enabled or task.schedule_type == "manual":
        remove_task(task.id)
        return

    job_id = _job_id(task.id)
    try:
        trigger = _trigger_for_task(task)
    except InvalidScheduleError:
        with SessionLocal() as db:
            db_task = db.get(TaskDefinition, task.id)
            if db_task:
                db_task.next_run_at = None
                db_task.scheduler_job_id = None
                db.commit()
        raise

    try:
        _scheduler.add_job(
            _run_task_job,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            kwargs={"task_id": task.id},
            max_instances=1,
            coalesce=True,
            misfire_grace_time=30,
        )

        job = _scheduler.get_job(job_id)
        with SessionLocal() as db:
            db_task = db.get(TaskDefinition, task.id)
            if db_task:
                db_task.scheduler_job_id = job_id
                db_task.next_run_at = job.next_run_time if job else None
                db.commit()

        logger.info(
            "Scheduler task registered: task_id=%s job_id=%s schedule_type=%s next_run=%s",
            task.id,
            job_id,
            task.schedule_type,
            job.next_run_time if job else None,
        )
    except Exception as exc:
        logger.exception("Scheduler register failed: task_id=%s", task.id)
        raise SchedulerRegistrationError(f"Failed to register scheduler job for task {task.id}") from exc


def update_task_schedule(task: TaskDefinition) -> None:
    """Update scheduler state after task modifications."""

    register_task(task)
    logger.info("Scheduler task updated: task_id=%s", task.id)


def remove_task(task_id: int) -> None:
    """Remove a task from scheduler and clear schedule metadata."""

    job_id = _job_id(task_id)
    try:
        if _scheduler.get_job(job_id):
            _scheduler.remove_job(job_id)

        with SessionLocal() as db:
            db_task = db.get(TaskDefinition, task_id)
            if db_task:
                db_task.next_run_at = None
                db_task.scheduler_job_id = None
                db.commit()

        logger.info("Scheduler task removed: task_id=%s job_id=%s", task_id, job_id)
    except Exception as exc:
        logger.exception("Scheduler remove failed: task_id=%s", task_id)
        raise SchedulerRegistrationError(f"Failed to remove scheduler job for task {task_id}") from exc


def get_job_for_task(task_id: int):
    return _scheduler.get_job(_job_id(task_id))


def list_registered_jobs() -> list:
    return list(_scheduler.get_jobs())


def get_scheduler_jobs() -> list[dict[str, str | int | bool | None]]:
    jobs = []
    with SessionLocal() as db:
        for job in _scheduler.get_jobs():
            task_id = None
            if job.id.startswith("task:"):
                try:
                    task_id = int(job.id.split(":", maxsplit=1)[1])
                except ValueError:
                    task_id = None
            task = db.get(TaskDefinition, task_id) if task_id else None
            jobs.append(
                {
                    "job_id": job.id,
                    "task_id": task_id,
                    "task_name": task.name if task else None,
                    "trigger": str(job.trigger),
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                    "is_enabled": bool(task.is_enabled) if task else False,
                }
            )
    return jobs


def sync_enabled_tasks() -> None:
    """Sync DB tasks to APScheduler jobs.

    Startup-safe: logs per-task errors and continues.
    """

    with SessionLocal() as db:
        tasks = db.execute(select(TaskDefinition).order_by(TaskDefinition.id.asc())).scalars().all()

    task_map = {task.id: task for task in tasks}

    # Remove stale job ids not present in DB
    for job in list(_scheduler.get_jobs()):
        if not job.id.startswith("task:"):
            continue
        try:
            task_id = int(job.id.split(":", maxsplit=1)[1])
        except ValueError:
            continue
        if task_id not in task_map:
            try:
                _scheduler.remove_job(job.id)
            except Exception:
                logger.exception("Failed to remove stale scheduler job: job_id=%s", job.id)

    success_count = 0
    fail_count = 0
    removed_count = 0

    for task in tasks:
        try:
            if task.is_enabled and task.schedule_type in {"cron", "interval"}:
                register_task(task)
                success_count += 1
            else:
                remove_task(task.id)
                removed_count += 1
        except (InvalidScheduleError, SchedulerRegistrationError) as exc:
            fail_count += 1
            logger.error("Scheduler sync failed for task_id=%s name=%s: %s", task.id, task.name, exc)

    logger.info(
        "Scheduler sync completed: total=%s registered=%s removed=%s failed=%s",
        len(tasks),
        success_count,
        removed_count,
        fail_count,
    )
