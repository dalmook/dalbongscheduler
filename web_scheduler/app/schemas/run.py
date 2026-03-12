from datetime import datetime

from pydantic import BaseModel


class TaskRunListItem(BaseModel):
    id: int
    task_id: int
    trigger_type: str
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    result_summary: str | None
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskRunResponse(TaskRunListItem):
    pass


class TaskRunStartResponse(BaseModel):
    task_id: int
    run_id: int
    status: str
    message: str
