# .claudebot/api/routes/tasks.py
"""Task endpoints"""

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging

from ..auth import verify_api_key
from ...db.models import TaskStatus as DBTaskStatus
from ..enums import TaskType, TaskStatus

logger = logging.getLogger(__name__)

router = APIRouter()

# Global task manager - will be set on startup
_task_manager = None


def set_task_manager(manager):
    """Set the global task manager instance"""
    global _task_manager
    _task_manager = manager


def get_task_manager():
    """Get the task manager instance"""
    return _task_manager


class CreateTaskRequest(BaseModel):
    type: TaskType
    description: str
    files: List[str] = []
    branch: str = "main"
    priority: int = 0


class CreateTaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    created_at: datetime


class TaskDetailResponse(BaseModel):
    id: str
    type: TaskType
    status: TaskStatus
    description: str
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@router.post("/tasks", response_model=CreateTaskResponse)
async def create_task(request: CreateTaskRequest, http_request: Request, _: bool = Depends(verify_api_key)):
    """Create a new task and add to queue"""
    manager = get_task_manager()
    if not manager:
        raise HTTPException(status_code=503, detail="Task manager not initialized")

    try:
        task_data = {
            "type": request.type.value,
            "description": request.description,
            "files": request.files,
            "branch": request.branch,
            "priority": request.priority,
            "repo_path": str(http_request.app.state.repo_path) if hasattr(http_request.app.state, "repo_path") else "."
        }

        task = await manager.create_task(task_data)

        return CreateTaskResponse(
            task_id=task.id,
            status=TaskStatus(task.status.value),
            created_at=datetime.fromisoformat(task.created_at)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to create task")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks", response_model=List[TaskDetailResponse])
async def list_tasks(status_filter: Optional[TaskStatus] = None, limit: int = 50, _: bool = Depends(verify_api_key)):
    """List all tasks"""
    manager = get_task_manager()
    if not manager:
        return []

    try:
        # Import here to avoid circular import
        from ...db.models import TaskStatus as DBTaskStatus

        db_status = None
        if status_filter:
            db_status = DBTaskStatus(status_filter.value)
        task_list = await manager.list_tasks(status=db_status, limit=limit)

        return [
            TaskDetailResponse(
                id=task.id,
                type=TaskType(task.type.value),
                status=TaskStatus(task.status.value),
                description=task.description,
                result=eval(task.result) if task.result else None,
                error=task.error,
                created_at=datetime.fromisoformat(task.created_at),
                started_at=datetime.fromisoformat(task.started_at) if task.started_at else None,
                completed_at=datetime.fromisoformat(task.completed_at) if task.completed_at else None
            )
            for task in task_list
        ]
    except Exception as e:
        logger.exception("Failed to list tasks")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}", response_model=TaskDetailResponse)
async def get_task(task_id: str, _: bool = Depends(verify_api_key)):
    """Get task details"""
    manager = get_task_manager()
    if not manager:
        raise HTTPException(status_code=503, detail="Task manager not initialized")

    task = await manager.get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskDetailResponse(
        id=task.id,
        type=TaskType(task.type.value),
        status=TaskStatus(task.status.value),
        description=task.description,
        result=eval(task.result) if task.result else None,
        error=task.error,
        created_at=datetime.fromisoformat(task.created_at),
        started_at=datetime.fromisoformat(task.started_at) if task.started_at else None,
        completed_at=datetime.fromisoformat(task.completed_at) if task.completed_at else None
    )


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str, _: bool = Depends(verify_api_key)):
    """Cancel a running task"""
    manager = get_task_manager()
    if not manager:
        raise HTTPException(status_code=503, detail="Task manager not initialized")

    task = await manager.get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    success = await manager.cancel_task(task_id)
    if success:
        return {"status": "cancelled", "task_id": task_id}
    else:
        return {"status": "cancel_failed", "task_id": task_id}
