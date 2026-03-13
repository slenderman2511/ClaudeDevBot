"""
Observability Dashboard Module

Provides execution logs, agent status, and task metrics.
Can serve as a simple status endpoint or be integrated with a web dashboard.
"""

import json
import logging
import time
import threading
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class ExecutionLog:
    """Represents a single execution log entry."""
    timestamp: datetime
    level: LogLevel
    agent: str
    task_id: str
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentStatus:
    """Status of an agent."""
    name: str
    status: str  # idle, running, error
    current_task: Optional[str] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    last_execution: Optional[datetime] = None
    avg_execution_time: float = 0.0


@dataclass
class TaskMetric:
    """Metrics for a task."""
    task_id: str
    agent: str
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    error: Optional[str] = None


class ObservabilityDashboard:
    """
    Observability dashboard for tracking execution logs, agent status, and metrics.

    Provides:
    - Execution logging
    - Agent status tracking
    - Task metrics collection
    - JSON endpoints for dashboard integration
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the dashboard."""
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._logs: deque = deque(maxlen=1000)
        self._agent_status: Dict[str, AgentStatus] = {}
        self._task_metrics: Dict[str, TaskMetric] = {}
        self._metrics_lock = threading.Lock()

        # Configuration
        self._max_logs = 1000
        self._log_retention_hours = 24

        self._initialized = True
        logger.info("ObservabilityDashboard initialized")

    # Logging methods

    def log(self, level: LogLevel, agent: str, task_id: str, message: str, **metadata):
        """Log an execution event."""
        entry = ExecutionLog(
            timestamp=datetime.now(),
            level=level,
            agent=agent,
            task_id=task_id,
            message=message,
            metadata=metadata
        )

        with self._lock:
            self._logs.append(entry)

        # Also log to standard logger
        log_msg = f"[{agent}] {message}"
        if level == LogLevel.ERROR:
            logger.error(log_msg)
        elif level == LogLevel.WARNING:
            logger.warning(log_msg)
        elif level == LogLevel.DEBUG:
            logger.debug(log_msg)
        else:
            logger.info(log_msg)

    def info(self, agent: str, task_id: str, message: str, **metadata):
        """Log info level message."""
        self.log(LogLevel.INFO, agent, task_id, message, **metadata)

    def error(self, agent: str, task_id: str, message: str, **metadata):
        """Log error level message."""
        self.log(LogLevel.ERROR, agent, task_id, message, **metadata)

    def warning(self, agent: str, task_id: str, message: str, **metadata):
        """Log warning level message."""
        self.log(LogLevel.WARNING, agent, task_id, message, **metadata)

    # Agent status methods

    def register_agent(self, name: str):
        """Register an agent with the dashboard."""
        if name not in self._agent_status:
            self._agent_status[name] = AgentStatus(name=name, status="idle")
            self.info("dashboard", "system", f"Registered agent: {name}")

    def update_agent_status(self, name: str, status: str, task_id: Optional[str] = None):
        """Update agent status."""
        if name in self._agent_status:
            self._agent_status[name].status = status
            self._agent_status[name].current_task = task_id
            if status == "running":
                self._agent_status[name].last_execution = datetime.now()

    def record_agent_completion(self, name: str, success: bool, duration: float):
        """Record task completion for an agent."""
        if name in self._agent_status:
            agent = self._agent_status[name]
            if success:
                agent.tasks_completed += 1
            else:
                agent.tasks_failed += 1

            # Update average execution time
            total = agent.tasks_completed + agent.tasks_failed
            agent.avg_execution_time = (
                (agent.avg_execution_time * (total - 1) + duration) / total
            )

    # Task metrics methods

    def start_task(self, task_id: str, agent: str) -> str:
        """Start tracking a task."""
        with self._metrics_lock:
            metric = TaskMetric(
                task_id=task_id,
                agent=agent,
                status="running",
                start_time=datetime.now()
            )
            self._task_metrics[task_id] = metric

        self.info(agent, task_id, f"Task started")
        return task_id

    def complete_task(self, task_id: str, success: bool, error: Optional[str] = None):
        """Complete a task and record metrics."""
        with self._metrics_lock:
            if task_id in self._task_metrics:
                metric = self._task_metrics[task_id]
                metric.end_time = datetime.now()
                metric.duration = (metric.end_time - metric.start_time).total_seconds()
                metric.status = "completed" if success else "failed"
                metric.error = error

        if success:
            self.info(metric.agent, task_id, f"Task completed in {metric.duration:.2f}s")
        else:
            self.error(metric.agent, task_id, f"Task failed: {error}")

    # Query methods

    def get_recent_logs(self, limit: int = 50, level: Optional[LogLevel] = None) -> List[Dict]:
        """Get recent logs."""
        with self._lock:
            logs = list(self._logs)

        if level:
            logs = [l for l in logs if l.level == level]

        return [
            {
                "timestamp": log.timestamp.isoformat(),
                "level": log.level.value,
                "agent": log.agent,
                "task_id": log.task_id,
                "message": log.message,
                "metadata": log.metadata
            }
            for log in logs[-limit:]
        ]

    def get_agent_statuses(self) -> List[Dict]:
        """Get all agent statuses."""
        return [
            {
                "name": agent.name,
                "status": agent.status,
                "current_task": agent.current_task,
                "tasks_completed": agent.tasks_completed,
                "tasks_failed": agent.tasks_failed,
                "last_execution": agent.last_execution.isoformat() if agent.last_execution else None,
                "avg_execution_time": round(agent.avg_execution_time, 2)
            }
            for agent in self._agent_status.values()
        ]

    def get_task_metrics(self, limit: int = 20) -> List[Dict]:
        """Get task metrics."""
        with self._metrics_lock:
            tasks = list(self._task_metrics.values())

        return [
            {
                "task_id": task.task_id,
                "agent": task.agent,
                "status": task.status,
                "start_time": task.start_time.isoformat(),
                "end_time": task.end_time.isoformat() if task.end_time else None,
                "duration": round(task.duration, 2) if task.duration else None,
                "error": task.error
            }
            for task in sorted(tasks, key=lambda t: t.start_time, reverse=True)[:limit]
        ]

    def get_summary(self) -> Dict:
        """Get overall summary."""
        with self._metrics_lock:
            total_tasks = len(self._task_metrics)
            completed = sum(1 for t in self._task_metrics.values() if t.status == "completed")
            failed = sum(1 for t in self._task_metrics.values() if t.status == "failed")

        return {
            "timestamp": datetime.now().isoformat(),
            "agents": {
                "total": len(self._agent_status),
                "running": sum(1 for a in self._agent_status.values() if a.status == "running"),
                "idle": sum(1 for a in self._agent_status.values() if a.status == "idle"),
                "error": sum(1 for a in self._agent_status.values() if a.status == "error")
            },
            "tasks": {
                "total": total_tasks,
                "completed": completed,
                "failed": failed,
                "success_rate": round(completed / total_tasks * 100, 1) if total_tasks > 0 else 0
            },
            "logs": {
                "total": len(self._logs),
                "errors": sum(1 for l in self._logs if l.level == LogLevel.ERROR)
            }
        }

    def get_dashboard_data(self) -> Dict:
        """Get all dashboard data for rendering."""
        return {
            "summary": self.get_summary(),
            "agents": self.get_agent_statuses(),
            "recent_logs": self.get_recent_logs(20),
            "task_metrics": self.get_task_metrics(10)
        }

    def clear_old_data(self, hours: int = 24):
        """Clear logs older than specified hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        with self._lock:
            self._logs = deque(
                (log for log in self._logs if log.timestamp > cutoff),
                maxlen=self._max_logs
            )


# Global dashboard instance
_dashboard: Optional[ObservabilityDashboard] = None


def get_dashboard() -> ObservabilityDashboard:
    """Get the global dashboard instance."""
    global _dashboard
    if _dashboard is None:
        _dashboard = ObservabilityDashboard()
    return _dashboard
