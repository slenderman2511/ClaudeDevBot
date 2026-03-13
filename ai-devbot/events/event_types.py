"""
Event Types Module

Defines all system events for event-driven architecture.
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


class EventType(Enum):
    """System event types."""

    # Feature events
    FEATURE_CREATED = "feature_created"
    FEATURE_UPDATED = "feature_updated"
    FEATURE_DELETED = "feature_deleted"

    # Specification events
    SPEC_UPDATED = "spec_updated"
    SPEC_VALIDATED = "spec_validated"

    # Task events
    TASK_GRAPH_CREATED = "task_graph_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_SKIPPED = "task_skipped"

    # Agent events
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"

    # Workflow events
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"

    # Execution events
    CODE_GENERATED = "code_generated"
    CODE_APPLIED = "code_applied"

    # Testing events
    TEST_RUN = "test_run"
    TEST_COMPLETED = "test_completed"
    TEST_FAILED = "test_failed"

    # Deployment events
    DEPLOY_STARTED = "deploy_started"
    DEPLOY_COMPLETED = "deploy_completed"
    DEPLOY_FAILED = "deploy_failed"

    # Debug events
    DEBUG_STARTED = "debug_started"
    DEBUG_COMPLETED = "debug_completed"

    # System events
    SYSTEM_ERROR = "system_error"
    SYSTEM_READY = "system_ready"


@dataclass
class Event:
    """Base event class."""

    type: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "system"
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "source": self.source,
            "correlation_id": self.correlation_id
        }


# Feature Events
@dataclass
class FeatureCreatedEvent(Event):
    """Event emitted when a feature is created."""

    def __init__(self, feature_name: str, **kwargs):
        super().__init__(
            type=EventType.FEATURE_CREATED,
            data={"feature_name": feature_name, **kwargs}
        )


@dataclass
class FeatureUpdatedEvent(Event):
    """Event emitted when a feature is updated."""

    def __init__(self, feature_name: str, changes: Dict[str, Any], **kwargs):
        super().__init__(
            type=EventType.FEATURE_UPDATED,
            data={"feature_name": feature_name, "changes": changes, **kwargs}
        )


# Task Events
@dataclass
class TaskGraphCreatedEvent(Event):
    """Event emitted when a task graph is created."""

    def __init__(self, feature_name: str, task_count: int, **kwargs):
        super().__init__(
            type=EventType.TASK_GRAPH_CREATED,
            data={"feature_name": feature_name, "task_count": task_count, **kwargs}
        )


@dataclass
class TaskStartedEvent(Event):
    """Event emitted when a task starts execution."""

    def __init__(self, task_id: str, agent_name: str, **kwargs):
        super().__init__(
            type=EventType.TASK_STARTED,
            data={"task_id": task_id, "agent_name": agent_name, **kwargs}
        )


@dataclass
class TaskCompletedEvent(Event):
    """Event emitted when a task completes."""

    def __init__(self, task_id: str, agent_name: str, duration: float, **kwargs):
        super().__init__(
            type=EventType.TASK_COMPLETED,
            data={
                "task_id": task_id,
                "agent_name": agent_name,
                "duration": duration,
                **kwargs
            }
        )


@dataclass
class TaskFailedEvent(Event):
    """Event emitted when a task fails."""

    def __init__(self, task_id: str, agent_name: str, error: str, **kwargs):
        super().__init__(
            type=EventType.TASK_FAILED,
            data={"task_id": task_id, "agent_name": agent_name, "error": error, **kwargs}
        )


# Agent Events
@dataclass
class AgentStartedEvent(Event):
    """Event emitted when an agent starts."""

    def __init__(self, agent_name: str, task_id: str, **kwargs):
        super().__init__(
            type=EventType.AGENT_STARTED,
            data={"agent_name": agent_name, "task_id": task_id, **kwargs}
        )


@dataclass
class AgentCompletedEvent(Event):
    """Event emitted when an agent completes."""

    def __init__(self, agent_name: str, task_id: str, success: bool, **kwargs):
        super().__init__(
            type=EventType.AGENT_COMPLETED,
            data={"agent_name": agent_name, "task_id": task_id, "success": success, **kwargs}
        )


# Workflow Events
@dataclass
class WorkflowStartedEvent(Event):
    """Event emitted when a workflow starts."""

    def __init__(self, workflow_id: str, command: str, **kwargs):
        super().__init__(
            type=EventType.WORKFLOW_STARTED,
            data={"workflow_id": workflow_id, "command": command, **kwargs}
        )


@dataclass
class WorkflowCompletedEvent(Event):
    """Event emitted when a workflow completes."""

    def __init__(self, workflow_id: str, status: str, duration: float, **kwargs):
        super().__init__(
            type=EventType.WORKFLOW_COMPLETED,
            data={"workflow_id": workflow_id, "status": status, "duration": duration, **kwargs}
        )


# Deployment Events
@dataclass
class DeployStartedEvent(Event):
    """Event emitted when deployment starts."""

    def __init__(self, target: str, feature_name: str, **kwargs):
        super().__init__(
            type=EventType.DEPLOY_STARTED,
            data={"target": target, "feature_name": feature_name, **kwargs}
        )


@dataclass
class DeployCompletedEvent(Event):
    """Event emitted when deployment completes."""

    def __init__(self, target: str, feature_name: str, url: Optional[str] = None, **kwargs):
        super().__init__(
            type=EventType.DEPLOY_COMPLETED,
            data={"target": target, "feature_name": feature_name, "url": url, **kwargs}
        )


# Test Events
@dataclass
class TestCompletedEvent(Event):
    """Event emitted when tests complete."""

    def __init__(self, feature_name: str, passed: int, failed: int, duration: float, **kwargs):
        super().__init__(
            type=EventType.TEST_COMPLETED,
            data={
                "feature_name": feature_name,
                "passed": passed,
                "failed": failed,
                "duration": duration,
                **kwargs
            }
        )
