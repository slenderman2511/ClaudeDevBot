"""
Executor Module

Executes tasks from a task graph using agents.
"""

import asyncio
import time
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime

from claudebot.orchestrator.task_graph import TaskGraph, TaskItem, TaskState
from claudebot.agents.base_agent import Task, AgentResult
from claudebot.observability.logger import get_logger

logger = get_logger(__name__)


class Executor:
    """
    Executes tasks from a task graph using registered agents.

    Supports:
    - Sequential execution
    - Parallel execution within levels
    - Retry logic
    - Progress tracking
    """

    def __init__(self, max_workers: int = 4, retry_attempts: int = 3):
        """
        Initialize the executor.

        Args:
            max_workers: Maximum number of parallel workers
            retry_attempts: Number of retry attempts for failed tasks
        """
        self.max_workers = max_workers
        self.retry_attempts = retry_attempts
        self._agents: Dict[str, Any] = {}
        self._callbacks: Dict[str, List[Callable]] = {
            "on_task_start": [],
            "on_task_complete": [],
            "on_task_fail": [],
            "on_workflow_start": [],
            "on_workflow_complete": []
        }

    def register_agent(self, agent_type: str, agent: Any) -> None:
        """
        Register an agent for a specific type.

        Args:
            agent_type: Type of agent (code, test, deploy, etc.)
            agent: Agent instance
        """
        self._agents[agent_type] = agent
        logger.info(f"Registered agent: {agent_type}")

    def register_callback(self, event: str, callback: Callable) -> None:
        """
        Register a callback for an event.

        Args:
            event: Event name
            callback: Callback function
        """
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    async def execute(self, task_graph: TaskGraph, parallel: bool = True) -> Dict[str, Any]:
        """
        Execute a task graph.

        Args:
            task_graph: Task graph to execute
            parallel: Enable parallel execution within levels

        Returns:
            Execution results
        """
        start_time = time.time()

        logger.info(f"Starting execution of task graph: {task_graph.name}")
        self._trigger_callbacks("on_workflow_start", task_graph)

        # Calculate execution levels
        execution_levels = task_graph.calculate_execution_levels()
        logger.info(f"Execution plan: {len(execution_levels)} levels")

        completed_tasks: Set[str] = set()
        failed_tasks: List[str] = []

        # Execute each level
        for level_idx, level in enumerate(execution_levels):
            logger.info(f"Executing level {level_idx + 1}/{len(execution_levels)} with {len(level)} tasks")

            if parallel and len(level) > 1:
                # Execute tasks in parallel
                results = await self._execute_parallel(level)
            else:
                # Execute tasks sequentially
                results = await self._execute_sequential(level)

            # Process results
            for task, result in results:
                if result.success:
                    completed_tasks.add(task.id)
                    self._trigger_callbacks("on_task_complete", task, result)
                else:
                    failed_tasks.append(task.id)
                    self._trigger_callbacks("on_task_fail", task, result)

            # Stop if any task failed
            if failed_tasks:
                logger.warning(f"Task(s) failed: {failed_tasks}")
                break

        execution_time = time.time() - start_time

        # Trigger workflow complete
        self._trigger_callbacks("on_workflow_complete", task_graph, completed_tasks, failed_tasks)

        result = {
            "success": len(failed_tasks) == 0,
            "completed_tasks": len(completed_tasks),
            "failed_tasks": len(failed_tasks),
            "execution_time": execution_time,
            "stats": task_graph.get_stats()
        }

        logger.info(f"Execution complete: {result}")
        return result

    async def _execute_sequential(self, tasks: List[TaskItem]) -> List[tuple]:
        """Execute tasks sequentially."""
        results = []
        for task in tasks:
            result = await self._execute_task(task)
            results.append((task, result))
        return results

    async def _execute_parallel(self, tasks: List[TaskItem]) -> List[tuple]:
        """Execute tasks in parallel."""
        coroutines = [self._execute_task(task) for task in tasks]
        results = await asyncio.gather(*coroutines, return_exceptions=True)

        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                task = tasks[i]
                task.state = TaskState.FAILED
                task.error = str(result)
                processed_results.append((task, AgentResult(success=False, output="", error=str(result))))
            else:
                processed_results.append((tasks[i], result))

        return processed_results

    async def _execute_task(self, task: TaskItem) -> AgentResult:
        """
        Execute a single task.

        Args:
            task: Task to execute

        Returns:
            Agent result
        """
        task.state = TaskState.RUNNING
        task.started_at = datetime.now()

        self._trigger_callbacks("on_task_start", task)

        logger.info(f"Executing task: {task.id} - {task.name}")

        # Get the appropriate agent
        agent = self._agents.get(task.agent_type)
        if not agent:
            task.state = TaskState.FAILED
            task.error = f"No agent registered for type: {task.agent_type}"
            return AgentResult(success=False, output="", error=task.error)

        # Create agent task
        agent_task = Task(
            id=task.id,
            type=task.agent_type,
            input=task.input_data if isinstance(task.input_data, str) else str(task.input_data),
            context=task.metadata
        )

        # Execute with retry logic
        for attempt in range(self.retry_attempts):
            try:
                # Execute in thread pool to avoid blocking
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: agent.execute(agent_task)
                )

                if result.success:
                    task.state = TaskState.COMPLETED
                    task.result = result
                    task.completed_at = datetime.now()
                    return result
                else:
                    if attempt < self.retry_attempts - 1:
                        logger.warning(f"Task {task.id} failed, retrying ({attempt + 1}/{self.retry_attempts})")
                        await asyncio.sleep(1)  # Brief delay before retry

            except Exception as e:
                logger.error(f"Task {task.id} raised exception: {e}")
                task.error = str(e)

        # All retries exhausted
        task.state = TaskState.FAILED
        task.error = task.error or "Max retries exceeded"
        task.completed_at = datetime.now()

        return AgentResult(success=False, output="", error=task.error)

    def _trigger_callbacks(self, event: str, *args, **kwargs):
        """Trigger all registered callbacks for an event."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Callback error in {event}: {e}")


def create_executor(
    max_workers: int = 4,
    retry_attempts: int = 3
) -> Executor:
    """
    Create an executor instance.

    Args:
        max_workers: Maximum number of parallel workers
        retry_attempts: Number of retry attempts

    Returns:
        Executor instance
    """
    return Executor(max_workers=max_workers, retry_attempts=retry_attempts)
