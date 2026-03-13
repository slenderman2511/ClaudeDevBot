"""
Orchestration Module

Coordinates agent execution and manages multi-agent workflows.
"""

import logging
import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum

from agents.base_agent import BaseAgent, Task, AgentResult
from workflows.command_router import CommandType

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowStep:
    """Represents a single step in a workflow."""
    step_id: str
    agent_name: str
    task: Task
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[AgentResult] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


@dataclass
class Workflow:
    """Represents a complete workflow."""
    workflow_id: str
    command_type: CommandType
    steps: List[WorkflowStep] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    context: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def completed_steps(self) -> int:
        return sum(1 for s in self.steps if s.status == TaskStatus.COMPLETED)


class Orchestrator:
    """
    Orchestrates multi-agent workflows.

    Manages the execution of tasks across multiple agents.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the orchestrator.

        Args:
            config: Orchestrator configuration
        """
        self.config = config or {}
        self.max_concurrent = self.config.get('max_concurrent_tasks', 5)
        self.task_timeout = self.config.get('task_timeout_seconds', 600)
        self.retry_attempts = self.config.get('retry_attempts', 3)
        self.retry_delay = self.config.get('retry_delay_seconds', 5)

        self._agents: Dict[str, BaseAgent] = {}
        self._workflows: Dict[str, Workflow] = {}
        self._callbacks: Dict[str, List[Callable]] = {
            'on_workflow_start': [],
            'on_workflow_complete': [],
            'on_step_complete': [],
            'on_error': []
        }
        self._logger = logging.getLogger(__name__)

    def register_agent(self, agent: BaseAgent):
        """Register an agent with the orchestrator."""
        self._agents[agent.name] = agent
        logger.info(f"Registered agent: {agent.name}")

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get an agent by name."""
        return self._agents.get(name)

    def list_agents(self) -> List[BaseAgent]:
        """List all registered agents."""
        return list(self._agents.values())

    def register_callback(self, event: str, callback: Callable):
        """Register a callback for workflow events."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _trigger_callbacks(self, event: str, *args, **kwargs):
        """Trigger registered callbacks."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Callback error for {event}: {e}")

    def create_workflow(
        self,
        workflow_id: str = None,
        command_type: CommandType = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Workflow:
        """
        Create a new workflow.

        Args:
            workflow_id: Unique workflow identifier (auto-generated if None)
            command_type: Type of command to execute
            context: Workflow context

        Returns:
            Created workflow
        """
        if workflow_id is None:
            workflow_id = str(uuid.uuid4())[:8]

        workflow = Workflow(
            workflow_id=workflow_id,
            command_type=command_type,
            context=context or {}
        )
        self._workflows[workflow_id] = workflow
        logger.info(f"Created workflow: {workflow_id} for command: {command_type.value if command_type else 'unknown'}")
        return workflow

    def add_step(self, workflow: Workflow, agent_name: str, task: Task) -> WorkflowStep:
        """
        Add a step to a workflow.

        Args:
            workflow: Target workflow
            agent_name: Name of agent to execute
            task: Task to execute

        Returns:
            Created workflow step
        """
        step = WorkflowStep(
            step_id=f"{workflow.workflow_id}_step_{len(workflow.steps)}",
            agent_name=agent_name,
            task=task
        )
        workflow.steps.append(step)
        return step

    async def execute_workflow(self, workflow: Workflow) -> Workflow:
        """
        Execute a workflow with parallel execution support.

        Args:
            workflow: Workflow to execute

        Returns:
            Completed workflow
        """
        logger.info(f"Executing workflow: {workflow.workflow_id}")
        workflow.status = TaskStatus.RUNNING
        self._trigger_callbacks('on_workflow_start', workflow)

        # Check if we have task graph data for parallel execution
        execution_levels = workflow.context.get('execution_levels')
        if execution_levels:
            # Use parallel execution
            workflow = await self._execute_parallel(workflow, execution_levels)
        else:
            # Sequential execution
            workflow = await self._execute_sequential(workflow)

        if workflow.status == TaskStatus.RUNNING:
            workflow.status = TaskStatus.COMPLETED

        workflow.completed_at = datetime.now()
        logger.info(f"Workflow {workflow.workflow_id} completed with status: {workflow.status.value}")
        self._trigger_callbacks('on_workflow_complete', workflow)

        return workflow

    async def _execute_sequential(self, workflow: Workflow) -> Workflow:
        """Execute workflow steps sequentially."""
        for step in workflow.steps:
            if workflow.status == TaskStatus.CANCELLED:
                break

            try:
                step.status = TaskStatus.RUNNING
                step.started_at = datetime.now()

                agent = self.get_agent(step.agent_name)
                if agent is None:
                    raise ValueError(f"Agent not found: {step.agent_name}")

                # Execute agent
                result = await asyncio.wait_for(
                    asyncio.to_thread(agent.execute, step.task),
                    timeout=self.task_timeout
                )

                step.result = result
                step.status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
                step.completed_at = datetime.now()

                self._trigger_callbacks('on_step_complete', workflow, step)

                if not result.success:
                    logger.error(f"Step {step.step_id} failed: {result.error}")
                    workflow.status = TaskStatus.FAILED
                    self._trigger_callbacks('on_error', workflow, step, result.error)
                    break

            except asyncio.TimeoutError:
                step.status = TaskStatus.FAILED
                step.error = f"Task timeout after {self.task_timeout}s"
                workflow.status = TaskStatus.FAILED
                self._trigger_callbacks('on_error', workflow, step, step.error)
                break

            except Exception as e:
                step.status = TaskStatus.FAILED
                step.error = str(e)
                workflow.status = TaskStatus.FAILED
                logger.error(f"Step {step.step_id} error: {e}")
                self._trigger_callbacks('on_error', workflow, step, str(e))
                break

        return workflow

    async def _execute_parallel(self, workflow: Workflow, execution_levels: List[List[dict]]) -> Workflow:
        """Execute workflow with parallel execution at each level."""
        step_map = {}  # Maps step_id to WorkflowStep

        for level_idx, level in enumerate(execution_levels):
            logger.info(f"Executing level {level_idx + 1}/{len(execution_levels)} with {len(level)} parallel tasks")

            # Create tasks for parallel execution
            tasks = []
            step_objects = []

            for task_data in level:
                step_id = task_data.get('step_id', f"parallel_{level_idx}_{len(tasks)}")
                agent_name = task_data.get('agent_name', 'code_agent')
                task_input = task_data.get('task', Task(input="")).input if hasattr(task_data.get('task'), 'input') else task_data.get('task', "")

                # Create step
                step = WorkflowStep(
                    step_id=step_id,
                    agent_name=agent_name,
                    task=task_input
                )
                step.status = TaskStatus.RUNNING
                step.started_at = datetime.now()
                workflow.steps.append(step)
                step_map[step_id] = step

                # Create async task
                agent = self.get_agent(agent_name)
                if agent:
                    task = asyncio.create_task(
                        self._execute_step_async(agent, step, workflow)
                    )
                    tasks.append(task)
                    step_objects.append(step)

            # Wait for all parallel tasks to complete
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Check for failures
                for i, result in enumerate(results):
                    step = step_objects[i]
                    if isinstance(result, Exception):
                        step.status = TaskStatus.FAILED
                        step.error = str(result)
                        workflow.status = TaskStatus.FAILED
                        self._trigger_callbacks('on_error', workflow, step, str(result))
                    elif not result.success:
                        step.status = TaskStatus.FAILED
                        workflow.status = TaskStatus.FAILED
                        self._trigger_callbacks('on_error', workflow, step, result.error)

                # Stop if workflow failed
                if workflow.status == TaskStatus.FAILED:
                    break

        return workflow

    async def _execute_step_async(self, agent: BaseAgent, step: WorkflowStep, workflow: Workflow) -> AgentResult:
        """Execute a single step asynchronously."""
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(agent.execute, step.task),
                timeout=self.task_timeout
            )
            step.result = result
            step.status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
            step.completed_at = datetime.now()
            self._trigger_callbacks('on_step_complete', workflow, step)
            return result
        except asyncio.TimeoutError:
            step.status = TaskStatus.FAILED
            step.error = f"Task timeout after {self.task_timeout}s"
            step.completed_at = datetime.now()
            raise Exception(step.error)
        except Exception as e:
            step.status = TaskStatus.FAILED
            step.error = str(e)
            step.completed_at = datetime.now()
            raise

    async def execute_workflow_with_retry(self, workflow: Workflow) -> Workflow:
        """Execute workflow with retry on failure."""
        last_error = None

        for attempt in range(self.retry_attempts):
            if attempt > 0:
                logger.info(f"Retry attempt {attempt + 1} for workflow {workflow.workflow_id}")
                await asyncio.sleep(self.retry_delay * attempt)

            workflow = await self.execute_workflow(workflow)

            if workflow.status == TaskStatus.COMPLETED:
                return workflow

            last_error = workflow.steps[-1].error if workflow.steps else "Unknown error"

        # All retries failed
        logger.error(f"Workflow {workflow.workflow_id} failed after {self.retry_attempts} attempts")
        return workflow

    def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow."""
        workflow = self._workflows.get(workflow_id)
        if workflow and workflow.status == TaskStatus.RUNNING:
            workflow.status = TaskStatus.CANCELLED
            return True
        return False

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow by ID."""
        return self._workflows.get(workflow_id)

    def list_workflows(self, status: TaskStatus = None) -> List[Workflow]:
        """List all workflows, optionally filtered by status."""
        workflows = list(self._workflows.values())
        if status:
            workflows = [w for w in workflows if w.status == status]
        return workflows

    def get_workflow_summary(self) -> Dict[str, Any]:
        """Get summary of all workflows."""
        all_workflows = list(self._workflows.values())
        return {
            'total': len(all_workflows),
            'pending': len([w for w in all_workflows if w.status == TaskStatus.PENDING]),
            'running': len([w for w in all_workflows if w.status == TaskStatus.RUNNING]),
            'completed': len([w for w in all_workflows if w.status == TaskStatus.COMPLETED]),
            'failed': len([w for w in all_workflows if w.status == TaskStatus.FAILED]),
        }
