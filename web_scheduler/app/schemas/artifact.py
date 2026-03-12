from datetime import datetime

from pydantic import BaseModel


class TaskArtifactListItem(BaseModel):
    id: int
    task_id: int
    run_id: int
    artifact_type: str
    is_latest: bool
    version_no: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskArtifactResponse(TaskArtifactListItem):
    content_text: str | None
    content_html: str | None
    content_json: str | None
