from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.db.models import TaskArtifact
from app.schemas.artifact import TaskArtifactResponse
from app.services.exceptions import TaskArtifactNotFoundError


def create_artifact(
    db: Session,
    *,
    task_id: int,
    run_id: int,
    artifact_type: str,
    content_text: str | None,
    content_html: str | None,
    content_json: str | None,
) -> TaskArtifact:
    db.execute(
        update(TaskArtifact)
        .where(TaskArtifact.task_id == task_id, TaskArtifact.is_latest.is_(True))
        .values(is_latest=False)
    )

    current_version = db.execute(select(func.max(TaskArtifact.version_no)).where(TaskArtifact.task_id == task_id)).scalar()
    next_version = (current_version or 0) + 1

    artifact = TaskArtifact(
        task_id=task_id,
        run_id=run_id,
        artifact_type=artifact_type,
        content_text=content_text,
        content_html=content_html,
        content_json=content_json,
        is_latest=True,
        version_no=next_version,
    )
    db.add(artifact)
    db.flush()
    return artifact


def list_artifacts(
    db: Session,
    *,
    task_id: int | None = None,
    run_id: int | None = None,
    is_latest: bool | None = None,
) -> list[TaskArtifact]:
    stmt = select(TaskArtifact)
    if task_id is not None:
        stmt = stmt.where(TaskArtifact.task_id == task_id)
    if run_id is not None:
        stmt = stmt.where(TaskArtifact.run_id == run_id)
    if is_latest is not None:
        stmt = stmt.where(TaskArtifact.is_latest == is_latest)

    return list(db.execute(stmt.order_by(TaskArtifact.created_at.desc())).scalars().all())


def get_artifact(db: Session, artifact_id: int) -> TaskArtifact:
    artifact = db.get(TaskArtifact, artifact_id)
    if not artifact:
        raise TaskArtifactNotFoundError("Artifact not found")
    return artifact


def to_artifact_response(artifact: TaskArtifact) -> TaskArtifactResponse:
    return TaskArtifactResponse.model_validate(artifact)
