"""
Task Graph Module

Provides task graph data structures for orchestration.
"""

from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from devbot.observability.logger import get_logger

logger = get_logger(__name__)


class TaskState(Enum):
    """Task execution state."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class TaskItem:
    """Represents a task in the execution graph."""
    id: str
    name: str
    description: str = ""
    phase: str = "Implementation"
    agent_type: str = "code"
    input_data: Any = None
    dependencies: List[str] = field(default_factory=list)
    state: TaskState = TaskState.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_ready(self) -> bool:
        """Check if task is ready to execute."""
        return self.state == TaskState.PENDING

    def can_execute(self, completed_tasks: Set[str]) -> bool:
        """Check if all dependencies are met."""
        return all(dep in completed_tasks for dep in self.dependencies)


class TaskGraph:
    """
    Directed acyclic graph of tasks for execution.
    """

    def __init__(self, name: str):
        """
        Initialize the task graph.

        Args:
            name: Name of the task graph
        """
        self.name = name
        self.tasks: Dict[str, TaskItem] = {}
        self.execution_levels: List[List[TaskItem]] = []

    def add_task(self, task: TaskItem) -> None:
        """
        Add a task to the graph.

        Args:
            task: Task to add
        """
        self.tasks[task.id] = task
        logger.debug(f"Added task: {task.id} - {task.name}")

    def add_tasks(self, tasks: List[TaskItem]) -> None:
        """
        Add multiple tasks to the graph.

        Args:
            tasks: List of tasks to add
        """
        for task in tasks:
            self.add_task(task)

    def get_task(self, task_id: str) -> Optional[TaskItem]:
        """Get a task by ID."""
        return self.tasks.get(task_id)

    def get_ready_tasks(self, completed_tasks: Set[str]) -> List[TaskItem]:
        """
        Get tasks that are ready to execute.

        Args:
            completed_tasks: Set of completed task IDs

        Returns:
            List of tasks ready for execution
        """
        ready = []
        for task in self.tasks.values():
            if task.is_ready() and task.can_execute(completed_tasks):
                ready.append(task)
        return ready

    def get_tasks_by_phase(self, phase: str) -> List[TaskItem]:
        """Get all tasks in a specific phase."""
        return [t for t in self.tasks.values() if t.phase == phase]

    def get_tasks_by_state(self, state: TaskState) -> List[TaskItem]:
        """Get all tasks with a specific state."""
        return [t for t in self.tasks.values() if t.state == state]

    def calculate_execution_levels(self) -> List[List[TaskItem]]:
        """
        Calculate execution levels using topological sort.

        Returns:
            List of levels, where each level contains tasks that can run in parallel
        """
        if self.execution_levels:
            return self.execution_levels

        levels = []
        completed: Set[str] = set()
        remaining = set(self.tasks.keys())

        while remaining:
            # Find all tasks whose dependencies are met
            current_level = []
            for task_id in remaining:
                task = self.tasks[task_id]
                if task.can_execute(completed):
                    current_level.append(task)

            if not current_level:
                logger.warning("Circular dependency detected in task graph")
                break

            levels.append(current_level)
            completed.update(t.id for t in current_level)
            remaining -= completed

        self.execution_levels = levels
        return levels

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the task graph."""
        return {
            "total_tasks": len(self.tasks),
            "pending": len(self.get_tasks_by_state(TaskState.PENDING)),
            "running": len(self.get_tasks_by_state(TaskState.RUNNING)),
            "completed": len(self.get_tasks_by_state(TaskState.COMPLETED)),
            "failed": len(self.get_tasks_by_state(TaskState.FAILED)),
            "execution_levels": len(self.calculate_execution_levels())
        }

    def reset(self) -> None:
        """Reset all task states to pending."""
        for task in self.tasks.values():
            task.state = TaskState.PENDING
            task.result = None
            task.error = None
            task.started_at = None
            task.completed_at = None
        self.execution_levels = []


def create_task_graph(name: str, tasks: List[Dict[str, Any]]) -> TaskGraph:
    """
    Create a task graph from a list of task dictionaries.

    Args:
        name: Name of the task graph
        tasks: List of task dictionaries

    Returns:
        TaskGraph instance
    """
    graph = TaskGraph(name)

    for task_dict in tasks:
        task = TaskItem(
            id=task_dict.get("id", f"task_{len(graph.tasks)}"),
            name=task_dict.get("name", "Unnamed Task"),
            description=task_dict.get("description", ""),
            phase=task_dict.get("phase", "Implementation"),
            agent_type=task_dict.get("agent_type", "code"),
            input_data=task_dict.get("input"),
            dependencies=task_dict.get("dependencies", []),
            priority=TaskPriority[task_dict.get("priority", "MEDIUM").upper()]
        )
        graph.add_task(task)

    return graph
