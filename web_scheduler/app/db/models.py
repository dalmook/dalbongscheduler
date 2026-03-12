from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    runs: Mapped[list["TaskRun"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="desc(TaskRun.created_at)",
    )
    artifacts: Mapped[list["TaskArtifact"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="desc(TaskArtifact.created_at)",
    )


class TaskRun(Base):
    """Execution history for manual/scheduled task runs."""

    __tablename__ = "task_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("task_definitions.id", ondelete="CASCADE"), nullable=False, index=True)

    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False, default="manual", index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued", index=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    task: Mapped[TaskDefinition] = relationship(back_populates="runs")
    artifacts: Mapped[list["TaskArtifact"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="desc(TaskArtifact.created_at)",
    )


class TaskArtifact(Base):
    """Versioned output artifacts produced by a task run."""

    __tablename__ = "task_artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("task_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("task_runs.id", ondelete="CASCADE"), nullable=False, index=True)

    artifact_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_latest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    task: Mapped[TaskDefinition] = relationship(back_populates="artifacts")
    run: Mapped[TaskRun] = relationship(back_populates="artifacts")
