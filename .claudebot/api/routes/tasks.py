# .claudebot/api/routes/tasks.py
"""Task endpoints"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid

router = APIRouter()

class TaskType(str, Enum):
    SPEC = "spec"
    CODE = "code"
    TEST = "test"
    DEPLOY = "deploy"
    DEBUG = "debug"

class TaskStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

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

# In-memory storage (will be replaced with orchestrator)
tasks_db: dict[str, TaskDetailResponse] = {}

@router.post("/tasks", response_model=CreateTaskResponse)
async def create_task(request: CreateTaskRequest):
    task_id = str(uuid.uuid4())
    task = TaskDetailResponse(
        id=task_id,
        type=request.type,
        status=TaskStatus.PENDING,
        description=request.description,
        created_at=datetime.now()
    )
    tasks_db[task_id] = task
    return CreateTaskResponse(
        task_id=task_id,
        status=task.status,
        created_at=task.created_at
    )

@router.get("/tasks", response_model=List[TaskDetailResponse])
async def list_tasks():
    return list(tasks_db.values())

@router.get("/tasks/{task_id}", response_model=TaskDetailResponse)
async def get_task(task_id: str):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks_db[task_id]

@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    task = tasks_db[task_id]
    task.status = TaskStatus.CANCELLED
    return {"status": "cancelled"}
