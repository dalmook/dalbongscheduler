from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.artifact import TaskArtifactListItem, TaskArtifactResponse
from app.services.artifact_service import get_artifact, list_artifacts
from app.services.exceptions import TaskArtifactNotFoundError

router = APIRouter(tags=["artifacts"])


@router.get("/artifacts", response_model=list[TaskArtifactListItem])
def list_artifacts_api(
    task_id: int | None = Query(default=None),
    run_id: int | None = Query(default=None),
    is_latest: bool | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[TaskArtifactListItem]:
    artifacts = list_artifacts(db, task_id=task_id, run_id=run_id, is_latest=is_latest)
    return [TaskArtifactListItem.model_validate(item) for item in artifacts]


@router.get("/artifacts/{artifact_id}", response_model=TaskArtifactResponse)
def get_artifact_api(artifact_id: int, db: Session = Depends(get_db)) -> TaskArtifactResponse:
    try:
        artifact = get_artifact(db, artifact_id)
        return TaskArtifactResponse.model_validate(artifact)
    except TaskArtifactNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/tasks/{task_id}/artifacts", response_model=list[TaskArtifactListItem])
def list_task_artifacts_api(task_id: int, db: Session = Depends(get_db)) -> list[TaskArtifactListItem]:
    artifacts = list_artifacts(db, task_id=task_id)
    return [TaskArtifactListItem.model_validate(item) for item in artifacts]


@router.get("/artifacts/{artifact_id}/preview", response_class=HTMLResponse)
def preview_artifact_api(artifact_id: int, db: Session = Depends(get_db)) -> HTMLResponse:
    try:
        artifact = get_artifact(db, artifact_id)
    except TaskArtifactNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if artifact.artifact_type == "html":
        html = artifact.content_html or "<html><body><p>(empty html artifact)</p></body></html>"
    elif artifact.artifact_type in {"json", "csv", "text"}:
        text = artifact.content_text or artifact.content_json or ""
        html = f"<html><body><pre>{text}</pre></body></html>"
    else:
        html = "<html><body><pre>Unsupported artifact preview type</pre></body></html>"

    return HTMLResponse(content=html, status_code=status.HTTP_200_OK)
