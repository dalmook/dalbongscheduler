from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TaskDefinition(Base):
    """Stores user-defined tasks with executable payload placeholders."""

    __tablename__ = "task_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    task_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    schedule_type: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    cron_expr: Mapped[str | None] = mapped_column(String(100), nullable=True)
    interval_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    python_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    sql_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    html_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    params_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_format: Mapped[str | None] = mapped_column(String(20), nullable=True)

    last_run_status: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
