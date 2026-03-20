"""
Planner Agent Module

Agent responsible for generating executable task graphs from OpenSpec features.
"""

import logging
import time
from typing import Dict, Any, Optional, List

from .base_agent import BaseAgent, AgentContext, AgentResult
from ..tools.claude_cli import ClaudeCLI

logger = logging.getLogger(__name__)


class TaskPriority:
    """Task priority levels."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


class TaskStatus:
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskNode:
    """Represents a single task in the execution graph."""

    def __init__(self, task_id: str, name: str, phase: str, dependencies: List[str] = None):
        self.task_id = task_id
        self.name = name
        self.phase = phase
        self.dependencies = dependencies or []
        self.status = TaskStatus.PENDING
        self.priority = TaskPriority.MEDIUM
        self.agent_type = self._infer_agent_type(phase)
        self.metadata: Dict[str, Any] = {}

    def _infer_agent_type(self, phase: str) -> str:
        """Infer which agent should handle this task based on phase."""
        phase_lower = phase.lower()
        if "design" in phase_lower:
            return "spec"
        elif "implementation" in phase_lower:
            return "code"
        elif "test" in phase_lower:
            return "test"
        elif "deploy" in phase_lower:
            return "deploy"
        else:
            return "code"


class TaskGraph:
    """Directed acyclic graph of tasks."""

    def __init__(self, feature_name: str):
        self.feature_name = feature_name
        self.nodes: Dict[str, TaskNode] = {}
        self.execution_order: List[List[TaskNode]] = []

    def add_task(self, task: TaskNode):
        """Add a task to the graph."""
        self.nodes[task.task_id] = task

    def get_ready_tasks(self) -> List[TaskNode]:
        """Get tasks that are ready to execute (all dependencies met)."""
        ready = []
        for task in self.nodes.values():
            if task.status == TaskStatus.PENDING:
                deps_met = all(
                    self.nodes.get(dep_id, TaskNode("", "", "")).status == TaskStatus.COMPLETED
                    for dep_id in task.dependencies
                )
                if deps_met:
                    ready.append(task)
        return ready

    def topological_sort(self) -> List[List[TaskNode]]:
        """Return tasks in execution order (parallel levels)."""
        if self.execution_order:
            return self.execution_order

        in_degree = {tid: len(t.dependencies) for tid, t in self.nodes.items()}
        levels = []

        while len(levels) < len(self.nodes):
            current_level = [
                tid for tid, deg in in_degree.items()
                if deg == 0 and self.nodes[tid].status == TaskStatus.PENDING
            ]

            if not current_level:
                break

            levels.append([self.nodes[tid] for tid in current_level])

            for tid in current_level:
                in_degree[tid] = -1
                for other_id, other_task in self.nodes.items():
                    if tid in other_task.dependencies:
                        in_degree[other_id] -= 1

        self.execution_order = levels
        return levels


class PlannerAgent(BaseAgent):
    """
    Agent responsible for planning and scheduling tasks from OpenSpec.

    Generates optimized task graphs with parallel execution support.
    """

    name = "planner"
    description = "Generate task graphs from OpenSpec features"

    def __init__(self, config: Dict[str, Any] = None, openspec=None):
        super().__init__()
        self._config = config or {}
        self._openspec = openspec
        self._generated_plans: Dict[str, TaskGraph] = {}

    async def execute(self, task: dict, context: AgentContext) -> AgentResult:
        """Execute planning task — generate task graph from feature."""
        is_valid, error = self.validate_input(task)
        if not is_valid:
            return AgentResult(success=False, summary=error, error=error)

        feature_name = task.get("description", "").strip()
        if not feature_name:
            return AgentResult(
                success=False,
                summary="Feature name is required",
                error="No feature name provided for planning",
            )

        logger.info(f"Planning tasks for feature: {feature_name}")

        try:
            # Load feature from OpenSpec
            if not self._openspec:
                return AgentResult(
                    success=False,
                    summary="OpenSpec not configured",
                    error="OpenSpec not configured",
                )

            feature = self._openspec.load_feature(feature_name)
            if not feature:
                return AgentResult(
                    success=False,
                    summary=f"Feature '{feature_name}' not found",
                    error=f"Feature '{feature_name}' not found in openspec/",
                )

            # Generate task graph
            task_graph = self._generate_task_graph(feature)

            # Store plan
            self._generated_plans[feature_name] = task_graph

            # Format output
            output = self._format_plan_output(task_graph)

            return AgentResult(
                success=True,
                summary=f"Generated plan for '{feature_name}' with {len(task_graph.nodes)} task(s)",
                logs=[output],
            )

        except Exception as e:
            logger.exception("Planner agent execution failed")
            return AgentResult(
                success=False,
                summary=f"Planning error: {e}",
                error=str(e),
            )

    def validate_input(self, task: dict) -> tuple[bool, Optional[str]]:
        """Validate task input."""
        if not task.get("description"):
            return False, "Feature name is required"
        return True, None

    def _generate_task_graph(self, feature: Dict[str, Any]) -> TaskGraph:
        """Generate task graph from feature spec."""
        graph = TaskGraph(feature.get("name", "unknown"))

        tasks = feature.get("tasks", [])
        phase_groups: Dict[str, List[Dict]] = {}

        # Group tasks by phase
        for task in tasks:
            phase = task.get("phase", "Implementation")
            if phase not in phase_groups:
                phase_groups[phase] = []
            phase_groups[phase].append(task)

        # Create task nodes with dependencies
        task_counter = 0
        for phase, phase_tasks in phase_groups.items():
            previous_tasks = []

            for task in phase_tasks:
                task_id = f"task_{task_counter}"
                task_counter += 1

                node = TaskNode(
                    task_id=task_id,
                    name=task.get("name", "Unnamed task"),
                    phase=phase,
                    dependencies=list(previous_tasks),
                )

                graph.add_task(node)
                previous_tasks.append(task_id)

        return graph

    def _format_plan_output(self, graph: TaskGraph) -> str:
        """Format task graph as readable output."""
        output = f"Task Plan: {graph.feature_name}\n\n"
        output += f"Total Tasks: {len(graph.nodes)}\n"

        levels = graph.topological_sort()
        output += f"Execution Levels: {len(levels)}\n\n"

        for i, level in enumerate(levels):
            output += f"Level {i + 1} (parallel):\n"
            for task in level:
                output += f"  - {task.name} [{task.agent_type}]\n"
            output += "\n"

        return output

    def get_plan(self, feature_name: str) -> Optional[TaskGraph]:
        """Get previously generated plan."""
        return self._generated_plans.get(feature_name)

    def get_capabilities(self) -> list:
        return [
            "generate_task_graph",
            "analyze_dependencies",
            "optimize_execution_order",
            "estimate_duration",
        ]
