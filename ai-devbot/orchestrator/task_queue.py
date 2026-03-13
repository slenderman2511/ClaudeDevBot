"""
Task Queue Module

Async task queue with priority support, backpressure handling, and worker pools.
"""

import asyncio
import logging
import uuid
import time
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from collections import deque
import heapq

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels (lower = higher priority)."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class TaskState(Enum):
    """Task execution state."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class QueuedTask:
    """A task in the queue."""

    id: str
    payload: Any
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_at: Optional[datetime] = None
    state: TaskState = TaskState.PENDING
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other):
        """Compare for heap ordering (priority + FIFO)."""
        if self.priority != other.priority:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at


class WorkerPool:
    """Pool of workers for executing tasks."""

    def __init__(self, size: int, worker_func: Callable):
        """
        Initialize worker pool.

        Args:
            size: Number of workers
            worker_func: Async function to execute for each task
        """
        self.size = size
        self.worker_func = worker_func
        self.workers: List[asyncio.Task] = []
        self.running: Set[str] = set()  # Task IDs currently running
        self.completed_count = 0
        self.failed_count = 0

    async def start(self):
        """Start all workers."""
        for i in range(self.size):
            task = asyncio.create_task(self._worker(i))
            self.workers.append(task)
        logger.info(f"Started {self.size} workers")

    async def _worker(self, worker_id: int):
        """Worker coroutine."""
        logger.debug(f"Worker {worker_id} started")

    async def stop(self):
        """Stop all workers."""
        for task in self.workers:
            task.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        logger.info(f"Worker pool stopped")


@dataclass
class TaskQueueMetrics:
    """Metrics for task queue."""
    queued: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0
    total_processed: int = 0
    avg_wait_time: float = 0.0
    avg_process_time: float = 0.0


class TaskQueue:
    """
    Async task queue with priority support.

    Features:
    - Priority-based ordering
    - Backpressure (max queue size)
    - Worker pool execution
    - Metrics collection
    - Task cancellation
    """

    def __init__(
        self,
        max_size: int = 1000,
        max_workers: int = 4,
        worker_func: Optional[Callable] = None
    ):
        """
        Initialize task queue.

        Args:
            max_size: Maximum queue size (0 = unlimited)
            max_workers: Number of concurrent workers
            worker_func: Function to process tasks
        """
        self.max_size = max_size
        self.max_workers = max_workers
        self.worker_func = worker_func

        self._queue: List[QueuedTask] = []
        self._tasks: Dict[str, QueuedTask] = {}
        self._results: Dict[str, Any] = {}
        self._locks = {
            'queue': asyncio.Lock(),
            'tasks': asyncio.Lock()
        }

        self._workers: List[asyncio.Task] = []
        self._running = False
        self._paused = False

        self._metrics = TaskQueueMetrics()
        self._wait_times: deque = deque(maxlen=100)
        self._process_times: deque = deque(maxlen=100)

        self._callbacks = {
            'on_enqueue': [],
            'on_dequeue': [],
            'on_complete': [],
            'on_error': []
        }

        logger.info(f"TaskQueue initialized (max_size={max_size}, workers={max_workers})")

    def _get_nowait_task(self) -> Optional[QueuedTask]:
        """Get next task without waiting (for worker loop)."""
        while self._queue:
            task = heapq.heappop(self._queue)
            # Skip cancelled tasks
            if task.state == TaskState.CANCELLED:
                continue
            return task
        return None

    async def enqueue(
        self,
        payload: Any,
        priority: TaskPriority = TaskPriority.NORMAL,
        task_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Add a task to the queue.

        Args:
            payload: Task data
            priority: Task priority
            task_id: Optional task ID
            metadata: Optional metadata

        Returns:
            Task ID
        """
        # Check backpressure
        if self.max_size > 0 and len(self._tasks) >= self.max_size:
            raise asyncio.QueueFull(f"Queue is full (max: {self.max_size})")

        task_id = task_id or str(uuid.uuid4())[:8]

        task = QueuedTask(
            id=task_id,
            payload=payload,
            priority=priority,
            metadata=metadata or {}
        )

        async with self._locks['tasks']:
            self._tasks[task_id] = task

        async with self._locks['queue']:
            heapq.heappush(self._queue, task)
            self._metrics.queued += 1

        # Trigger callback
        for cb in self._callbacks['on_enqueue']:
            try:
                cb(task)
            except Exception as e:
                logger.error(f"enqueue callback error: {e}")

        logger.debug(f"Enqueued task {task_id} with priority {priority.name}")
        return task_id

    async def dequeue(self, timeout: Optional[float] = None) -> Optional[QueuedTask]:
        """
        Get next task from queue.

        Args:
            timeout: Optional timeout in seconds

        Returns:
            Next task or None
        """
        start_time = time.time()

        while True:
            async with self._locks['queue']:
                task = self._get_nowait_task()

            if task:
                task.state = TaskState.QUEUED
                task.scheduled_at = datetime.now()

                # Track wait time
                wait_time = (task.scheduled_at - task.created_at).total_seconds()
                self._wait_times.append(wait_time)

                for cb in self._callbacks['on_dequeue']:
                    try:
                        cb(task)
                    except Exception as e:
                        logger.error(f"dequeue callback error: {e}")

                return task

            if timeout and time.time() - start_time > timeout:
                return None

            await asyncio.sleep(0.01)

    async def get_result(self, task_id: str, timeout: float = 60.0) -> Any:
        """
        Get result of a completed task.

        Args:
            task_id: Task ID
            timeout: Timeout in seconds

        Returns:
            Task result

        Raises:
            TimeoutError: If timeout exceeded
            ValueError: If task not found
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            async with self._locks['tasks']:
                task = self._tasks.get(task_id)

            if not task:
                raise ValueError(f"Task {task_id} not found")

            if task.state == TaskState.COMPLETED:
                return task.result

            if task.state == TaskState.FAILED:
                raise Exception(task.error)

            if task.state == TaskState.CANCELLED:
                raise asyncio.CancelledError("Task was cancelled")

            await asyncio.sleep(0.05)

        raise TimeoutError(f"Timeout waiting for task {task_id}")

    async def cancel(self, task_id: str) -> bool:
        """Cancel a task."""
        async with self._locks['tasks']:
            task = self._tasks.get(task_id)
            if task and task.state in [TaskState.PENDING, TaskState.QUEUED]:
                task.state = TaskState.CANCELLED
                self._metrics.cancelled += 1
                return True
        return False

    def get_status(self, task_id: str) -> Optional[TaskState]:
        """Get task state."""
        task = self._tasks.get(task_id)
        return task.state if task else None

    def get_metrics(self) -> Dict[str, Any]:
        """Get queue metrics."""
        return {
            "queued": len(self._queue),
            "running": self._metrics.running,
            "completed": self._metrics.completed,
            "failed": self._metrics.failed,
            "cancelled": self._metrics.cancelled,
            "total": self._metrics.total_processed,
            "avg_wait_time": sum(self._wait_times) / len(self._wait_times) if self._wait_times else 0,
            "avg_process_time": sum(self._process_times) / len(self._process_times) if self._process_times else 0
        }

    async def start_workers(self):
        """Start worker pool."""
        if self._running:
            return

        self._running = True

        async def worker_loop(worker_id: int):
            while self._running:
                try:
                    task = await self.dequeue(timeout=1.0)
                    if not task:
                        continue

                    # Execute task
                    task.state = TaskState.RUNNING
                    self._metrics.running += 1
                    self._metrics.queued -= 1

                    start_time = time.time()

                    try:
                        if self.worker_func:
                            result = await self.worker_func(task.payload)
                        else:
                            result = task.payload

                        task.result = result
                        task.state = TaskState.COMPLETED
                        self._metrics.completed += 1

                        # Track process time
                        process_time = time.time() - start_time
                        self._process_times.append(process_time)

                        for cb in self._callbacks['on_complete']:
                            try:
                                cb(task)
                            except Exception as e:
                                logger.error(f"complete callback error: {e}")

                    except Exception as e:
                        task.error = str(e)
                        task.state = TaskState.FAILED
                        self._metrics.failed += 1

                        for cb in self._callbacks['on_error']:
                            try:
                                cb(task)
                            except Exception as e:
                                logger.error(f"error callback error: {e}")

                    finally:
                        self._metrics.running -= 1
                        self._metrics.total_processed += 1

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Worker {worker_id} error: {e}")
                    await asyncio.sleep(0.1)

        # Create workers
        for i in range(self.max_workers):
            worker = asyncio.create_task(worker_loop(i))
            self._workers.append(worker)

        logger.info(f"Started {self.max_workers} workers")

    async def stop_workers(self):
        """Stop worker pool."""
        self._running = False

        for worker in self._workers:
            worker.cancel()

        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

        logger.info("Worker pool stopped")

    def on(self, event: str, callback: Callable):
        """Register event callback."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)


# Global queue instance
_task_queue: Optional[TaskQueue] = None


def get_task_queue() -> TaskQueue:
    """Get global task queue instance."""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue()
    return _task_queue
