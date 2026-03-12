from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.session import get_db
from app.schemas.run import TaskRunListItem, TaskRunResponse, TaskRunStartResponse
from app.services.execution_service import get_run, list_runs, run_task
from app.services.exceptions import (
    InvalidParamsJsonError,
    TaskExecutionError,
    TaskRunNotFoundError,
    UnsupportedTaskTypeError,
)
from app.services.task_service import TaskNotFoundError

router = APIRouter(tags=["runs"])
logger = get_logger(__name__)


@router.post("/tasks/{task_id}/run", response_model=TaskRunStartResponse, status_code=status.HTTP_201_CREATED)
def run_task_api(task_id: int, request: Request, db: Session = Depends(get_db)) -> TaskRunStartResponse:
    logger.info("request_id=%s run_task task_id=%s", getattr(request.state, "request_id", "-"), task_id)
    try:
        run = run_task(db, task_id=task_id, trigger_type="manual")
        return TaskRunStartResponse(
            task_id=task_id,
            run_id=run.id,
            status=run.status,
            message="Task executed",
        )
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (TaskExecutionError, InvalidParamsJsonError, UnsupportedTaskTypeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/runs", response_model=list[TaskRunListItem])
def list_runs_api(
    task_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    trigger_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[TaskRunListItem]:
    runs = list_runs(db, task_id=task_id, status=status, trigger_type=trigger_type)
    return [TaskRunListItem.model_validate(run) for run in runs]


@router.get("/runs/{run_id}", response_model=TaskRunResponse)
def get_run_api(run_id: int, db: Session = Depends(get_db)) -> TaskRunResponse:
    try:
        run = get_run(db, run_id)
        return TaskRunResponse.model_validate(run)
    except TaskRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/tasks/{task_id}/runs", response_model=list[TaskRunListItem])
def list_task_runs_api(task_id: int, db: Session = Depends(get_db)) -> list[TaskRunListItem]:
    runs = list_runs(db, task_id=task_id)
    return [TaskRunListItem.model_validate(run) for run in runs]
