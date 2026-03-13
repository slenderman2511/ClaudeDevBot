"""
Orchestration Module

Coordinates agent execution and manages multi-agent workflows.
"""

import logging
import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
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
        self._logger = logging.getLogger(__name__)

    def register_agent(self, agent: BaseAgent):
        """Register an agent with the orchestrator."""
        self._agents[agent.name] = agent
        logger.info(f"Registered agent: {agent.name}")

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get an agent by name."""
        return self._agents.get(name)

    def create_workflow(
        self,
        workflow_id: str,
        command_type: CommandType,
        context: Optional[Dict[str, Any]] = None
    ) -> Workflow:
        """
        Create a new workflow.

        Args:
            workflow_id: Unique workflow identifier
            command_type: Type of command to execute
            context: Workflow context

        Returns:
            Created workflow
        """
        workflow = Workflow(
            workflow_id=workflow_id,
            command_type=command_type,
            context=context or {}
        )
        self._workflows[workflow_id] = workflow
        logger.info(f"Created workflow: {workflow_id} for command: {command_type.value}")
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
        Execute a workflow.

        Args:
            workflow: Workflow to execute

        Returns:
            Completed workflow
        """
        logger.info(f"Executing workflow: {workflow.workflow_id}")
        workflow.status = TaskStatus.RUNNING

        for step in workflow.steps:
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

                if not result.success:
                    logger.error(f"Step {step.step_id} failed: {result.error}")
                    workflow.status = TaskStatus.FAILED
                    break

            except asyncio.TimeoutError:
                step.status = TaskStatus.FAILED
                step.error = f"Task timeout after {self.task_timeout}s"
                workflow.status = TaskStatus.FAILED
                break

            except Exception as e:
                step.status = TaskStatus.FAILED
                step.error = str(e)
                workflow.status = TaskStatus.FAILED
                logger.error(f"Step {step.step_id} error: {e}")
                break

        if workflow.status == TaskStatus.RUNNING:
            workflow.status = TaskStatus.COMPLETED

        workflow.completed_at = datetime.now()
        logger.info(f"Workflow {workflow.workflow_id} completed with status: {workflow.status.value}")

        return workflow

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow by ID."""
        return self._workflows.get(workflow_id)

    def list_workflows(self) -> List[Workflow]:
        """List all workflows."""
        return list(self._workflows.values())
