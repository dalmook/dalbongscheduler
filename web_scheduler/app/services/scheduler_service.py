from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import TaskDefinition
from app.db.session import SessionLocal

logger = get_logger(__name__)
_settings = get_settings()
_scheduler = BackgroundScheduler(timezone=_settings.default_timezone)


def init_scheduler() -> None:
    """Initialize scheduler resources.

    TODO(phase3): configure persistent job stores and executors.
    """

    logger.info("Scheduler initialized")


def start_scheduler() -> None:
    if not _scheduler.running:
        _scheduler.start()
        logger.info("Scheduler started")


def shutdown_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler shutdown complete")


def sync_enabled_tasks() -> None:
    """Read currently enabled tasks and log sync candidates.

    TODO(phase3): register/update cron/interval jobs into APScheduler.
    """

    with SessionLocal() as db:
        enabled_tasks = (
            db.query(TaskDefinition)
            .filter(TaskDefinition.is_enabled.is_(True))
            .order_by(TaskDefinition.id.asc())
            .all()
        )

    for task in enabled_tasks:
        logger.info(
            "Scheduler sync candidate: task_id=%s name=%s schedule_type=%s",
            task.id,
            task.name,
            task.schedule_type,
        )

    logger.info("Scheduler sync completed: enabled_task_count=%s", len(enabled_tasks))
