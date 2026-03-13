"""
Planner Agent Module

Agent responsible for generating executable task graphs from OpenSpec features.
Analyzes dependencies and creates optimized execution plans.
"""

import logging
import time
import uuid
from typing import Dict, Any, Optional, List, Set
from enum import Enum
from agents.base_agent import BaseAgent, Task, AgentResult
from tools.claude_cli import ClaudeCLITool

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


class TaskStatus(Enum):
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
        self.metadata = {}

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

        # Calculate in-degrees
        in_degree = {tid: len(t.dependencies) for tid, t in self.nodes.items()}
        levels = []

        while len(levels) < len(self.nodes):
            # Find all nodes with in-degree 0
            current_level = [tid for tid, deg in in_degree.items() if deg == 0 and self.nodes[tid].status == TaskStatus.PENDING]

            if not current_level:
                break

            levels.append([self.nodes[tid] for tid in current_level])

            # Remove processed nodes from graph
            for tid in current_level:
                in_degree[tid] = -1  # Mark as processed

                # Reduce in-degree for dependents
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

    def __init__(self, config: Dict[str, Any] = None, claude_tool: Optional[ClaudeCLITool] = None, openspec=None):
        super().__init__(
            name="planner_agent",
            model=config.get('model', 'sonnet') if config else 'sonnet',
            max_iterations=config.get('max_iterations', 5) if config else 5,
            timeout=config.get('timeout', 120) if config else 120,
            config=config or {}
        )
        self._claude = claude_tool or ClaudeCLITool(config.get('claude', {}))
        self._openspec = openspec
        self._generated_plans: Dict[str, TaskGraph] = {}

    def execute(self, task: Task) -> AgentResult:
        """
        Execute planning task - generate task graph from feature.

        Args:
            task: Task with feature name in input

        Returns:
            AgentResult with TaskGraph
        """
        start_time = time.time()

        if not task.input:
            return AgentResult(
                success=False,
                output="",
                error="No feature specified for planning"
            )

        feature_name = task.input.strip()
        logger.info(f"Planning tasks for feature: {feature_name}")

        try:
            # Load feature from OpenSpec
            if not self._openspec:
                return AgentResult(
                    success=False,
                    output="",
                    error="OpenSpec not configured"
                )

            feature = self._openspec.load_feature(feature_name)
            if not feature:
                return AgentResult(
                    success=False,
                    output="",
                    error=f"Feature '{feature_name}' not found"
                )

            # Generate task graph
            task_graph = self._generate_task_graph(feature)

            # Store plan
            self._generated_plans[feature_name] = task_graph

            # Format output
            output = self._format_plan_output(task_graph)

            execution_time = time.time() - start_time

            return AgentResult(
                success=True,
                output=output,
                artifacts={
                    'feature': feature_name,
                    'task_graph': task_graph,
                    'total_tasks': len(task_graph.nodes),
                    'parallel_levels': len(task_graph.topological_sort())
                },
                execution_time=execution_time,
                iterations=1
            )

        except Exception as e:
            logger.exception("Planner agent execution failed")
            return AgentResult(
                success=False,
                output="",
                error=f"Planning error: {str(e)}"
            )

    def _generate_task_graph(self, feature: Dict[str, Any]) -> TaskGraph:
        """Generate task graph from feature spec."""
        graph = TaskGraph(feature.get('name', 'unknown'))

        tasks = feature.get('tasks', [])
        phase_groups: Dict[str, List[Dict]] = {}

        # Group tasks by phase
        for task in tasks:
            phase = task.get('phase', 'Implementation')
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
                    name=task.get('name', 'Unnamed task'),
                    phase=phase,
                    dependencies=list(previous_tasks)  # Depends on all previous in phase
                )

                graph.add_task(node)
                previous_tasks.append(task_id)

        return graph

    def _format_plan_output(self, graph: TaskGraph) -> str:
        """Format task graph as readable output."""
        output = f"📋 Task Plan: {graph.feature_name}\n\n"
        output += f"Total Tasks: {len(graph.nodes)}\n"

        levels = graph.topological_sort()
        output += f"Execution Levels: {len(levels)}\n\n"

        for i, level in enumerate(levels):
            output += f"Level {i + 1} (parallel):\n"
            for task in level:
                output += f"  • {task.name} [{task.agent_type}]\n"
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
            "estimate_duration"
        ]
