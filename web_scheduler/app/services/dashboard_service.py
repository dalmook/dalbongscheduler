import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import TaskArtifact, TaskDefinition, TaskRun
from app.schemas.dashboard import (
    DashboardHtmlResultItem,
    DashboardSummaryResponse,
    NextScheduledRunItem,
    RecentFailedRunItem,
)
from app.services.scheduler_service import get_scheduler_jobs

logger = get_logger(__name__)


_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html_preview(html: str | None, limit: int = 240) -> str | None:
    if not html:
        return None
    text = _TAG_RE.sub("", html)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."


def get_dashboard_summary(db: Session) -> DashboardSummaryResponse:
    now = datetime.now(timezone.utc)
    since_24h = now - timedelta(hours=24)

    total_tasks = db.scalar(select(func.count(TaskDefinition.id))) or 0
    enabled_tasks = db.scalar(select(func.count(TaskDefinition.id)).where(TaskDefinition.is_enabled.is_(True))) or 0
    manual_tasks = db.scalar(select(func.count(TaskDefinition.id)).where(TaskDefinition.schedule_type == "manual")) or 0
    scheduled_tasks = (
        db.scalar(
            select(func.count(TaskDefinition.id)).where(
                and_(TaskDefinition.is_enabled.is_(True), TaskDefinition.schedule_type.in_(["cron", "interval"]))
            )
        )
        or 0
    )

    running_tasks = db.scalar(select(func.count(TaskRun.id)).where(TaskRun.status == "running")) or 0

    success_runs_24h = (
        db.scalar(select(func.count(TaskRun.id)).where(and_(TaskRun.status == "success", TaskRun.created_at >= since_24h))) or 0
    )
    failed_runs_24h = (
        db.scalar(select(func.count(TaskRun.id)).where(and_(TaskRun.status == "failed", TaskRun.created_at >= since_24h))) or 0
    )

    html_artifacts_24h = (
        db.scalar(
            select(func.count(TaskArtifact.id)).where(
                and_(TaskArtifact.artifact_type == "html", TaskArtifact.created_at >= since_24h)
            )
        )
        or 0
    )

    next_runs_rows = db.execute(
        select(TaskDefinition)
        .where(and_(TaskDefinition.is_enabled.is_(True), TaskDefinition.schedule_type.in_(["cron", "interval"])))
        .order_by(TaskDefinition.next_run_at.asc().nullslast())
        .limit(10)
    ).scalars().all()
    next_scheduled_runs = [
        NextScheduledRunItem(
            task_id=row.id,
            task_name=row.name,
            schedule_type=row.schedule_type,
            next_run_at=row.next_run_at,
        )
        for row in next_runs_rows
    ]

    failed_rows = db.execute(
        select(TaskRun, TaskDefinition.name)
        .join(TaskDefinition, TaskDefinition.id == TaskRun.task_id)
        .where(TaskRun.status == "failed")
        .order_by(TaskRun.finished_at.desc().nullslast(), TaskRun.created_at.desc())
        .limit(10)
    ).all()

    recent_failed_runs = [
        RecentFailedRunItem(
            run_id=run.id,
            task_id=run.task_id,
            task_name=task_name,
            error_message=run.error_message,
            finished_at=run.finished_at,
        )
        for run, task_name in failed_rows
    ]

    return DashboardSummaryResponse(
        total_tasks=total_tasks,
        enabled_tasks=enabled_tasks,
        manual_tasks=manual_tasks,
        scheduled_tasks=scheduled_tasks,
        running_tasks=running_tasks,
        success_runs_24h=success_runs_24h,
        failed_runs_24h=failed_runs_24h,
        html_artifacts_24h=html_artifacts_24h,
        next_scheduled_runs=next_scheduled_runs,
        recent_failed_runs=recent_failed_runs,
    )


def get_dashboard_jobs() -> list[dict[str, str | int | bool | None]]:
    return get_scheduler_jobs()


def get_dashboard_html_results(db: Session) -> list[DashboardHtmlResultItem]:
    html_tasks = db.execute(select(TaskDefinition).where(TaskDefinition.task_type == "html").order_by(TaskDefinition.id.asc())).scalars().all()

    items: list[DashboardHtmlResultItem] = []
    for task in html_tasks:
        latest_artifact = db.execute(
            select(TaskArtifact)
            .where(and_(TaskArtifact.task_id == task.id, TaskArtifact.is_latest.is_(True)))
            .order_by(TaskArtifact.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        last_success = db.execute(
            select(TaskRun)
            .where(and_(TaskRun.task_id == task.id, TaskRun.status == "success"))
            .order_by(TaskRun.finished_at.desc().nullslast(), TaskRun.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        last_failed = db.execute(
            select(TaskRun)
            .where(and_(TaskRun.task_id == task.id, TaskRun.status == "failed"))
            .order_by(TaskRun.finished_at.desc().nullslast(), TaskRun.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        preview_source = None
        if latest_artifact:
            if latest_artifact.artifact_type == "html":
                preview_source = latest_artifact.content_html
            else:
                preview_source = latest_artifact.content_text or latest_artifact.content_json

        items.append(
            DashboardHtmlResultItem(
                task_id=task.id,
                task_name=task.name,
                latest_run_status=task.last_run_status,
                latest_artifact_id=latest_artifact.id if latest_artifact else None,
                latest_generated_at=latest_artifact.created_at if latest_artifact else None,
                preview_text=_strip_html_preview(preview_source),
                has_error=(task.last_run_status == "failed"),
                last_success_at=last_success.finished_at if last_success else None,
                last_failed_at=last_failed.finished_at if last_failed else None,
            )
        )

    return items
