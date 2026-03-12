from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import GenericMessageResponse
from app.schemas.task import TaskCreate, TaskListItem, TaskResponse, TaskUpdate
from app.services.task_service import (
    TaskDuplicateNameError,
    TaskNotFoundError,
    create_task,
    delete_task,
    get_task,
    list_tasks,
    update_task,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task_api(payload: TaskCreate, db: Session = Depends(get_db)) -> TaskResponse:
    try:
        task = create_task(db, payload)
        return TaskResponse.model_validate(task)
    except TaskDuplicateNameError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=list[TaskListItem])
def list_tasks_api(
    name: str | None = Query(default=None),
    task_type: str | None = Query(default=None),
    is_enabled: bool | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[TaskListItem]:
    tasks = list_tasks(db, name=name, task_type=task_type, is_enabled=is_enabled)
    return [TaskListItem.model_validate(task) for task in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
def get_task_api(task_id: int, db: Session = Depends(get_db)) -> TaskResponse:
    try:
        task = get_task(db, task_id)
        return TaskResponse.model_validate(task)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("/{task_id}", response_model=TaskResponse)
def update_task_api(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)) -> TaskResponse:
    try:
        task = update_task(db, task_id, payload)
        return TaskResponse.model_validate(task)
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except TaskDuplicateNameError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete("/{task_id}", response_model=GenericMessageResponse)
def delete_task_api(task_id: int, db: Session = Depends(get_db)) -> GenericMessageResponse:
    try:
        delete_task(db, task_id)
        return GenericMessageResponse(message="Task deleted successfully")
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
