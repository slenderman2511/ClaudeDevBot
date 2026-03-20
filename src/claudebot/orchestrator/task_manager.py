# .claudebot/orchestrator/task_manager.py
"""Task manager with queue and agent execution"""

import asyncio
import os
import logging
from datetime import datetime
from typing import Optional
import uuid
import aiosqlite

from ..agents.base_agent import AgentContext
from ..agents.code_agent import CodeAgent
from ..db.models import Task, TaskType, TaskStatus, init_db, get_db

logger = logging.getLogger(__name__)


async def notify_task_update(task_id: str, status: str, result: dict = None, error: str = None):
    """Broadcast task update via WebSocket if available"""
    try:
        from ..api.routes.websocket import notify_task_update as ws_notify
        await ws_notify(task_id, status, result, error)
    except Exception:
        # WebSocket not available, ignore
        pass

# Try to import agents, handle if not available
try:
    from ..agents.spec_agent import SpecAgent
    SPEC_AGENT_AVAILABLE = True
except ImportError:
    SPEC_AGENT_AVAILABLE = False

try:
    from ..agents.test_agent import TestAgent
    TEST_AGENT_AVAILABLE = True
except ImportError:
    TEST_AGENT_AVAILABLE = False

try:
    from ..agents.deploy_agent import DeployAgent
    DEPLOY_AGENT_AVAILABLE = True
except ImportError:
    DEPLOY_AGENT_AVAILABLE = False

try:
    from ..agents.debug_agent import DebugAgent
    DEBUG_AGENT_AVAILABLE = True
except ImportError:
    DEBUG_AGENT_AVAILABLE = False


class TaskManager:
    """Manages task queue and agent execution"""

    def __init__(self, config: dict):
        self.config = config
        self.queue: asyncio.Queue = asyncio.Queue()
        self.running_tasks: dict[str, asyncio.Task] = {}
        self.cancelled_tasks: set[str] = set()

    async def start(self):
        """Start the task manager"""
        await init_db()
        asyncio.create_task(self._process_queue())

    async def create_task(self, task_data: dict) -> Task:
        """Create and queue a new task"""
        task_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        task = Task(
            id=task_id,
            type=TaskType(task_data["type"]),
            status=TaskStatus.PENDING,
            description=task_data["description"],
            repo_path=task_data.get("repo_path", os.getcwd()),
            branch=task_data.get("branch", "main"),
            files=str(task_data.get("files", [])),
            priority=task_data.get("priority", 0),
            created_at=now
        )

        # Save to database
        async with await get_db() as db:
            await db.execute("""
                INSERT INTO tasks (id, type, status, description, repo_path, branch, files, priority, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (task.id, task.type.value, task.status.value, task.description,
                  task.repo_path, task.branch, task.files, task.priority, task.created_at))
            await db.commit()

        await self.queue.put(task)
        return task

    async def _process_queue(self):
        """Main loop - processes queued tasks"""
        while True:
            task = await self.queue.get()
            await self._execute_task(task)
            self.queue.task_done()

    async def _execute_task(self, task: Task):
        """Execute a single task with the appropriate agent"""
        # Check if cancelled
        if task.id in self.cancelled_tasks:
            await self._update_status(task.id, TaskStatus.CANCELLED)
            await notify_task_update(task.id, "cancelled")
            return

        await self._update_status(task.id, TaskStatus.RUNNING, started_at=datetime.now().isoformat())
        await notify_task_update(task.id, "running")
        self.running_tasks[task.id] = asyncio.current_task()

        try:
            # Get agent
            agent = self._get_agent(task.type)

            # Create context
            context = AgentContext(
                repo_path=task.repo_path,
                branch=task.branch,
                claude_api_key=os.environ.get("CLAUDE_API_KEY", ""),
                config=self.config
            )

            # Execute
            task_dict = {
                "description": task.description,
                "files": eval(task.files) if task.files else []
            }

            result = await agent.execute(task_dict, context)

            # Check cancellation again
            if task.id in self.cancelled_tasks:
                await self._update_status(task.id, TaskStatus.CANCELLED)
                await notify_task_update(task.id, "cancelled")
            else:
                await self._update_status(
                    task.id,
                    TaskStatus.COMPLETED,
                    completed_at=datetime.now().isoformat(),
                    result=str(result.__dict__)
                )
                await notify_task_update(task.id, "completed", result=result.__dict__)

        except Exception as e:
            logger.exception(f"Task {task.id} failed")
            await self._update_status(
                task.id,
                TaskStatus.FAILED,
                completed_at=datetime.now().isoformat(),
                error=str(e)
            )
            await notify_task_update(task.id, "failed", error=str(e))

        finally:
            self.running_tasks.pop(task.id, None)

    def _get_agent(self, task_type: TaskType):
        """Get agent instance for task type"""
        agent_map = {
            TaskType.CODE: CodeAgent(),
        }

        if SPEC_AGENT_AVAILABLE:
            agent_map[TaskType.SPEC] = SpecAgent()

        if TEST_AGENT_AVAILABLE:
            agent_map[TaskType.TEST] = TestAgent()

        if DEPLOY_AGENT_AVAILABLE:
            agent_map[TaskType.DEPLOY] = DeployAgent()

        if DEBUG_AGENT_AVAILABLE:
            agent_map[TaskType.DEBUG] = DebugAgent()

        if task_type not in agent_map:
            raise ValueError(f"Unknown task type: {task_type}")

        return agent_map[task_type]

    async def _update_status(self, task_id: str, status: TaskStatus, **kwargs):
        """Update task status in database"""
        async with await get_db() as db:
            set_clauses = ["status = ?"]
            values = [status.value]

            for key, value in kwargs.items():
                set_clauses.append(f"{key} = ?")
                values.append(value)

            values.append(task_id)

            await db.execute(
                f"UPDATE tasks SET {', '.join(set_clauses)} WHERE id = ?",
                values
            )
            await db.commit()

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        self.cancelled_tasks.add(task_id)

        if task_id in self.running_tasks:
            self.running_tasks[task_id].cancel()
            return True
        return False

    async def get_task_status(self, task_id: str) -> Optional[Task]:
        """Get task status from database"""
        async with await get_db() as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return Task(**dict(row))
        return None

    async def list_tasks(self, status: Optional[TaskStatus] = None, limit: int = 50) -> list[Task]:
        """List tasks, optionally filtered by status"""
        async with await get_db() as db:
            db.row_factory = aiosqlite.Row
            if status:
                async with db.execute(
                    "SELECT * FROM tasks WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status.value, limit)
                ) as cursor:
                    rows = await cursor.fetchall()
            else:
                async with db.execute(
                    "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                ) as cursor:
                    rows = await cursor.fetchall()
            return [Task(**dict(row)) for row in rows]
