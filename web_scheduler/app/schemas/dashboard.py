from datetime import datetime

from pydantic import BaseModel


class NextScheduledRunItem(BaseModel):
    task_id: int
    task_name: str
    schedule_type: str
    next_run_at: datetime | None


class RecentFailedRunItem(BaseModel):
    run_id: int
    task_id: int
    task_name: str
    error_message: str | None
    finished_at: datetime | None


class DashboardSummaryResponse(BaseModel):
    total_tasks: int
    enabled_tasks: int
    manual_tasks: int
    scheduled_tasks: int
    running_tasks: int
    success_runs_24h: int
    failed_runs_24h: int
    html_artifacts_24h: int
    next_scheduled_runs: list[NextScheduledRunItem]
    recent_failed_runs: list[RecentFailedRunItem]


class DashboardJobItem(BaseModel):
    job_id: str
    task_id: int | None
    task_name: str | None
    trigger: str
    next_run_time: str | None
    is_enabled: bool


class DashboardHtmlResultItem(BaseModel):
    task_id: int
    task_name: str
    latest_run_status: str | None
    latest_artifact_id: int | None
    latest_generated_at: datetime | None
    preview_text: str | None
    has_error: bool
    last_success_at: datetime | None
    last_failed_at: datetime | None
