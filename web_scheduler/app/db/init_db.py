from app.core.logging import get_logger
from app.db.base import Base
from app.db.models import TaskDefinition  # noqa: F401
from app.db.session import engine

logger = get_logger(__name__)


def init_db() -> None:
    """Create database tables if they do not exist."""

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")
