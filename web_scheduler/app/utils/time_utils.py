from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def now_local() -> datetime:
    settings = get_settings()
    return datetime.now(tz=ZoneInfo(settings.default_timezone))
