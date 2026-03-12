from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.schemas.run import TaskRunListItem

TASK_TYPES = {"python", "sql", "html"}
SCHEDULE_TYPES = {"manual", "cron", "interval"}
MIN_INTERVAL_SECONDS = 10


class TaskBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    task_type: str
    schedule_type: str = "manual"
    cron_expr: str | None = None
    interval_seconds: int | None = Field(default=None, gt=0)
    is_enabled: bool = True
    timezone: str | None = "Asia/Seoul"

    python_code: str | None = None
    sql_code: str | None = None
    html_template: str | None = None
    params_json: str | None = None
    output_format: str | None = None

    @model_validator(mode="after")
    def validate_task_type_and_schedule(self) -> "TaskBase":
        if self.task_type not in TASK_TYPES:
            raise ValueError(f"task_type must be one of {sorted(TASK_TYPES)}")
        if self.schedule_type not in SCHEDULE_TYPES:
            raise ValueError(f"schedule_type must be one of {sorted(SCHEDULE_TYPES)}")

        if self.schedule_type == "cron" and not self.cron_expr:
            raise ValueError("cron_expr is required when schedule_type is 'cron'")
        if self.schedule_type == "interval":
            if not self.interval_seconds:
                raise ValueError("interval_seconds is required when schedule_type is 'interval'")
            if self.interval_seconds < MIN_INTERVAL_SECONDS:
                raise ValueError(f"interval_seconds must be >= {MIN_INTERVAL_SECONDS}")

        return self


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    task_type: str | None = None
    schedule_type: str | None = None
    cron_expr: str | None = None
    interval_seconds: int | None = Field(default=None, gt=0)
    is_enabled: bool | None = None
    timezone: str | None = None

    python_code: str | None = None
    sql_code: str | None = None
    html_template: str | None = None
    params_json: str | None = None
    output_format: str | None = None

    @model_validator(mode="after")
    def validate_partial_update(self) -> "TaskUpdate":
        if self.task_type is not None and self.task_type not in TASK_TYPES:
            raise ValueError(f"task_type must be one of {sorted(TASK_TYPES)}")
        if self.schedule_type is not None and self.schedule_type not in SCHEDULE_TYPES:
            raise ValueError(f"schedule_type must be one of {sorted(SCHEDULE_TYPES)}")

        if self.schedule_type == "cron" and self.cron_expr is None:
            raise ValueError("cron_expr is required when updating schedule_type to 'cron'")
        if self.schedule_type == "interval":
            if self.interval_seconds is None:
                raise ValueError("interval_seconds is required when updating schedule_type to 'interval'")
            if self.interval_seconds < MIN_INTERVAL_SECONDS:
                raise ValueError(f"interval_seconds must be >= {MIN_INTERVAL_SECONDS}")

        return self


class TaskListItem(BaseModel):
    id: int
    name: str
    task_type: str
    schedule_type: str
    is_enabled: bool
    timezone: str | None
    next_run_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskResponse(BaseModel):
    id: int
    name: str
    description: str | None
    task_type: str
    schedule_type: str
    cron_expr: str | None
    interval_seconds: int | None
    is_enabled: bool
    timezone: str | None
    next_run_at: datetime | None
    scheduler_job_id: str | None
    python_code: str | None
    sql_code: str | None
    html_template: str | None
    params_json: str | None
    output_format: str | None
    last_run_status: str | None
    last_run_at: datetime | None
    created_at: datetime
    updated_at: datetime
    recent_runs: list[TaskRunListItem] | None = None

    model_config = {"from_attributes": True}
