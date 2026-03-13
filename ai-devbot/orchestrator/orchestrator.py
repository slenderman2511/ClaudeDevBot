"""
Scalable Orchestrator Module

Multi-agent orchestration with worker pools, task queues, and parallel execution.
"""

import asyncio
import logging
import uuid
import time
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import defaultdict

from events.event_bus import get_event_bus, publish
from events.event_types import (
    WorkflowStartedEvent, WorkflowCompletedEvent,
    TaskStartedEvent, TaskCompletedEvent, TaskFailedEvent,
    AgentStartedEvent, AgentCompletedEvent
)
from orchestrator.task_queue import TaskQueue, TaskPriority, TaskState
from agents.base_agent import Task, AgentResult
from observability.dashboard import get_dashboard

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskNode:
    """Represents a task in the execution graph."""
    id: str
    name: str
    agent_type: str
    input: Any
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0


@dataclass
class WorkflowExecution:
    """Represents a workflow execution instance."""
    id: str
    name: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    tasks: Dict[str, TaskNode] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    context: Dict[str, Any] = field(default_factory=dict)
    parallel_levels: List[List[str]] = field(default_factory=list)

    @property
    def total_tasks(self) -> int:
        return len(self.tasks)

    @property
    def completed_tasks(self) -> int:
        return sum(1 for t in self.tasks.values() if t.status == "completed")

    @property
    def progress(self) -> float:
        if self.total_tasks == 0:
            return 0
        return (self.completed_tasks / self.total_tasks) * 100


class AgentPool:
    """Pool of agents for parallel execution."""

    def __init__(self, max_size: int = 10):
        self.max_size = max_size
        self._agents: Dict[str, Any] = {}
        self._available: asyncio.Queue = asyncio.Queue()
        self._busy: Set[str] = set()
        self._lock = asyncio.Lock()

    def register(self, agent_type: str, agent: Any):
        """Register an agent."""
        self._agents[agent_type] = agent
        logger.info(f"Registered agent: {agent_type}")

    async def acquire(self, agent_type: str, timeout: float = 30.0) -> Optional[Any]:
        """Acquire an agent for execution."""
        start = time.time()

        while time.time() - start < timeout:
            async with self._lock:
                if agent_type in self._agents and agent_type not in self._busy:
                    self._busy.add(agent_type)
                    return self._agents[agent_type]

            await asyncio.sleep(0.1)

        return self._agents.get(agent_type)

    async def release(self, agent_type: str):
        """Release an agent back to the pool."""
        async with self._lock:
            self._busy.discard(agent_type)

    def get_status(self) -> Dict[str, Any]:
        """Get pool status."""
        return {
            "total_agents": len(self._agents),
            "busy_agents": len(self._busy),
            "available_agents": len(self._agents) - len(self._busy),
            "agent_types": list(self._agents.keys())
        }


class ScalableOrchestrator:
    """
    Scalable orchestrator with worker pools and parallel execution.

    Features:
    - Worker pools for each agent type
    - Task queues with priority support
    - Parallel execution of independent tasks
    - Event-driven architecture
    - Observability integration
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the orchestrator.

        Args:
            config: Configuration dict
        """
        config = config or {}
        self.config = config

        self.max_workers = config.get('max_workers', 4)
        self.max_queue_size = config.get('max_queue_size', 100)
        self.task_timeout = config.get('task_timeout', 300)
        self.retry_attempts = config.get('retry_attempts', 3)

        self._workflows: Dict[str, WorkflowExecution] = {}
        self._agent_pool = AgentPool(max_size=self.max_workers)
        self._task_queue: Optional[TaskQueue] = None
        self._event_bus = get_event_bus()
        self._dashboard = get_dashboard()

        self._running = False
        self._lock = asyncio.Lock()

        logger.info("ScalableOrchestrator initialized")

    def register_agent(self, agent_type: str, agent: Any):
        """Register an agent with the pool."""
        self._agent_pool.register(agent_type, agent)
        self._dashboard.register_agent(agent_type)

    async def start(self):
        """Start the orchestrator."""
        if self._running:
            return

        self._running = True

        # Initialize task queue
        self._task_queue = TaskQueue(
            max_size=self.max_queue_size,
            max_workers=self.max_workers
        )
        await self._task_queue.start_workers()

        logger.info("ScalableOrchestrator started")

    async def stop(self):
        """Stop the orchestrator."""
        self._running = False

        if self._task_queue:
            await self._task_queue.stop_workers()

        logger.info("ScalableOrchestrator stopped")

    async def create_workflow(
        self,
        name: str,
        task_graph: Dict[str, TaskNode],
        context: Optional[Dict] = None
    ) -> WorkflowExecution:
        """
        Create a workflow execution.

        Args:
            name: Workflow name
            task_graph: Task DAG
            context: Optional context

        Returns:
            WorkflowExecution
        """
        workflow_id = str(uuid.uuid4())[:8]

        workflow = WorkflowExecution(
            id=workflow_id,
            name=name,
            tasks=task_graph,
            context=context or {}
        )

        # Calculate parallel execution levels
        workflow.parallel_levels = self._calculate_levels(task_graph)

        async with self._lock:
            self._workflows[workflow_id] = workflow

        # Publish event
        publish(WorkflowStartedEvent(workflow_id, name))

        logger.info(f"Created workflow {workflow_id} with {len(task_graph)} tasks")

        return workflow

    def _calculate_levels(self, task_graph: Dict[str, TaskNode]) -> List[List[str]]:
        """Calculate parallel execution levels."""
        levels = []
        completed: Set[str] = set()

        while len(completed) < len(task_graph):
            # Find tasks with all dependencies met
            current_level = []
            for task_id, task in task_graph.items():
                if task_id in completed:
                    continue
                deps_met = all(dep in completed for dep in task.dependencies)
                if deps_met:
                    current_level.append(task_id)

            if not current_level:
                break

            levels.append(current_level)
            completed.update(current_level)

        return levels

    async def execute_workflow(
        self,
        workflow: WorkflowExecution,
        parallel: bool = True
    ) -> WorkflowExecution:
        """
        Execute a workflow.

        Args:
            workflow: Workflow to execute
            parallel: Enable parallel execution

        Returns:
            Completed workflow
        """
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.now()

        logger.info(f"Executing workflow {workflow.id}")

        try:
            if parallel:
                await self._execute_parallel(workflow)
            else:
                await self._execute_sequential(workflow)

            # Check results
            failed = [t for t in workflow.tasks.values() if t.status == "failed"]
            if failed:
                workflow.status = WorkflowStatus.FAILED
            else:
                workflow.status = WorkflowStatus.COMPLETED

        except Exception as e:
            logger.error(f"Workflow {workflow.id} error: {e}")
            workflow.status = WorkflowStatus.FAILED

        finally:
            workflow.completed_at = datetime.now()

            # Publish event
            duration = (workflow.completed_at - workflow.started_at).total_seconds()
            publish(WorkflowCompletedEvent(
                workflow.id,
                workflow.status.value,
                duration
            ))

        logger.info(f"Workflow {workflow.id} {workflow.status.value} "
                   f"({workflow.completed_tasks}/{workflow.total_tasks} tasks)")

        return workflow

    async def _execute_sequential(self, workflow: WorkflowExecution):
        """Execute workflow tasks sequentially."""
        for level in workflow.parallel_levels:
            for task_id in level:
                task = workflow.tasks[task_id]
                await self._execute_task(workflow, task)

                if task.status == "failed":
                    return  # Stop on failure

    async def _execute_parallel(self, workflow: WorkflowExecution):
        """Execute workflow tasks in parallel at each level."""
        for level in workflow.parallel_levels:
            # Execute all tasks in level concurrently
            tasks = []
            for task_id in level:
                task = workflow.tasks[task_id]
                task_coro = self._execute_task(workflow, task)
                tasks.append(task_coro)

            # Wait for all to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check for failures
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    task = workflow.tasks[level[i]]
                    task.status = "failed"
                    task.error = str(result)

            # Stop if any failed
            if any(workflow.tasks[tid].status == "failed" for tid in level):
                return

    async def _execute_task(
        self,
        workflow: WorkflowExecution,
        task: TaskNode
    ) -> Any:
        """
        Execute a single task.

        Args:
            workflow: Parent workflow
            task: Task to execute

        Returns:
            Task result
        """
        task.status = "running"
        task.started_at = datetime.now()

        # Publish events
        publish(TaskStartedEvent(task.id, task.agent_type))
        self._dashboard.update_agent_status(task.agent_type, "running", task.id)

        logger.info(f"Executing task {task.id} with {task.agent_type}")

        try:
            # Acquire agent from pool
            agent = await self._agent_pool.acquire(task.agent_type, timeout=30.0)

            if not agent:
                raise Exception(f"No agent available for {task.agent_type}")

            try:
                # Create Task from input
                task_obj = Task(
                    id=task.id,
                    type=task.agent_type,
                    input=task.input if isinstance(task.input, str) else str(task.input)
                )

                # Execute via agent
                result = await asyncio.wait_for(
                    asyncio.to_thread(agent.execute, task_obj),
                    timeout=self.task_timeout
                )

                task.result = result
                task.status = "completed"
                task.completed_at = datetime.now()

                # Publish events
                duration = (task.completed_at - task.started_at).total_seconds()
                publish(TaskCompletedEvent(task.id, task.agent_type, duration))
                self._dashboard.record_agent_completion(task.agent_type, True, duration)

                return result

            finally:
                await self._agent_pool.release(task.agent_type)

        except asyncio.TimeoutError:
            task.status = "failed"
            task.error = f"Task timeout after {self.task_timeout}s"
            task.completed_at = datetime.now()

            publish(TaskFailedEvent(task.id, task.agent_type, task.error))
            self._dashboard.record_agent_completion(task.agent_type, False, self.task_timeout)

            raise

        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.completed_at = datetime.now()

            publish(TaskFailedEvent(task.id, task.agent_type, task.error))
            self._dashboard.record_agent_completion(task.agent_type, False, 0)

            raise

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowExecution]:
        """Get workflow by ID."""
        return self._workflows.get(workflow_id)

    def list_workflows(self, status: Optional[WorkflowStatus] = None) -> List[WorkflowExecution]:
        """List workflows, optionally filtered by status."""
        workflows = list(self._workflows.values())
        if status:
            workflows = [w for w in workflows if w.status == status]
        return workflows

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status."""
        return {
            "running": self._running,
            "workflows": {
                "total": len(self._workflows),
                "running": len([w for w in self._workflows.values() if w.status == WorkflowStatus.RUNNING]),
                "completed": len([w for w in self._workflows.values() if w.status == WorkflowStatus.COMPLETED]),
                "failed": len([w for w in self._workflows.values() if w.status == WorkflowStatus.FAILED])
            },
            "agent_pool": self._agent_pool.get_status(),
            "task_queue": self._task_queue.get_metrics() if self._task_queue else {}
        }


# Global orchestrator instance
_orchestrator: Optional[ScalableOrchestrator] = None


def get_orchestrator(config: Optional[Dict] = None) -> ScalableOrchestrator:
    """Get global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ScalableOrchestrator(config)
    return _orchestrator
