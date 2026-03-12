from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
_settings = get_settings()
_scheduler = BackgroundScheduler(timezone=_settings.default_timezone)


def init_scheduler() -> None:
    """Initialize scheduler resources.

    TODO: Add job stores/executors for production scaling.
    """

    logger.info("Scheduler initialized (skeleton mode)")


def start_scheduler() -> None:
    if not _scheduler.running:
        _scheduler.start()
        logger.info("Scheduler started")


def shutdown_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler shutdown complete")


def sync_enabled_tasks() -> None:
    """Placeholder for syncing DB task definitions to APScheduler jobs.

    TODO: In phase 2, map enabled task definitions to scheduler jobs.
    """

    logger.info("sync_enabled_tasks called (TODO placeholder)")
