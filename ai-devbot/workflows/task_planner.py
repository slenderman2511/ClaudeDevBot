"""
Task Planner Module

Creates execution plans from commands.
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from workflows.command_router import CommandType, ParsedCommand
from agents.base_agent import Task

logger = logging.getLogger(__name__)


@dataclass
class ExecutionStep:
    """Represents a single execution step."""
    step_order: int
    agent_name: str
    task_input: str
    depends_on: List[str] = None

    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []


@dataclass
class ExecutionPlan:
    """Complete execution plan for a command."""
    plan_id: str
    command_type: CommandType
    steps: List[ExecutionStep]
    estimated_duration: int  # seconds
    context: Dict[str, Any]


class TaskPlanner:
    """
    Creates execution plans from parsed commands.

    Determines which agents to use and in what order.
    """

    # Command to agent mapping
    COMMAND_AGENT_MAP = {
        CommandType.SPEC: {
            'agents': ['spec_agent'],
            'estimated_duration': 60
        },
        CommandType.CODE: {
            'agents': ['code_agent'],
            'estimated_duration': 120
        },
        CommandType.TEST: {
            'agents': ['test_agent'],
            'estimated_duration': 90
        },
        CommandType.DEPLOY: {
            'agents': ['deploy_agent'],
            'estimated_duration': 180
        },
        CommandType.DEBUG: {
            'agents': ['debug_agent'],
            'estimated_duration': 60
        },
        CommandType.STATUS: {
            'agents': [],
            'estimated_duration': 5
        }
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the task planner.

        Args:
            config: Planner configuration
        """
        self.config = config or {}
        self._logger = logging.getLogger(__name__)

    def create_plan(
        self,
        plan_id: str,
        parsed_command: ParsedCommand,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionPlan:
        """
        Create an execution plan from a parsed command.

        Args:
            plan_id: Unique plan identifier
            parsed_command: Parsed command
            context: Additional context

        Returns:
            Execution plan
        """
        command_config = self.COMMAND_AGENT_MAP.get(
            parsed_command.command_type,
            {'agents': [], 'estimated_duration': 30}
        )

        steps = []
        for i, agent_name in enumerate(command_config['agents']):
            step = ExecutionStep(
                step_order=i,
                agent_name=agent_name,
                task_input=parsed_command.arguments
            )
            steps.append(step)

        plan = ExecutionPlan(
            plan_id=plan_id,
            command_type=parsed_command.command_type,
            steps=steps,
            estimated_duration=command_config['estimated_duration'],
            context=context or {}
        )

        logger.info(f"Created plan {plan_id} with {len(steps)} steps for {parsed_command.command_type.value}")

        return plan

    def create_tasks(self, plan: ExecutionPlan) -> List[Task]:
        """
        Create tasks from an execution plan.

        Args:
            plan: Execution plan

        Returns:
            List of tasks to execute
        """
        tasks = []
        for step in plan.steps:
            task = Task(
                id=f"{plan.plan_id}_task_{step.step_order}",
                type=plan.command_type.value,
                input=step.task_input,
                context=plan.context
            )
            tasks.append(task)

        return tasks

    def get_supported_commands(self) -> List[CommandType]:
        """Get list of supported command types."""
        return list(self.COMMAND_AGENT_MAP.keys())

    def estimate_time(self, command_type: CommandType) -> int:
        """Estimate execution time for a command type."""
        config = self.COMMAND_AGENT_MAP.get(command_type)
        return config['estimated_duration'] if config else 30
