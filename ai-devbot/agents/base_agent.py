"""
Base Agent Module

Defines the abstract BaseAgent class that all specialized agents inherit from.
Provides common functionality for agent execution, validation, and capability reporting.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class Task:
    """Represents a task to be executed by an agent."""
    id: str
    type: str
    input: str
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Represents the result of agent execution."""
    success: bool
    output: str
    error: Optional[str] = None
    artifacts: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    iterations: int = 0


class BaseAgent(ABC):
    """
    Abstract base class for all AI agents.

    All specialized agents must inherit from this class and implement
    the execute method.
    """

    def __init__(
        self,
        name: str,
        model: str = "sonnet",
        max_iterations: int = 10,
        timeout: int = 300,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the agent.

        Args:
            name: Agent name identifier
            model: AI model to use
            max_iterations: Maximum execution iterations
            timeout: Execution timeout in seconds
            config: Additional configuration
        """
        self.name = name
        self.model = model
        self.max_iterations = max_iterations
        self.timeout = timeout
        self.config = config or {}
        self._logger = logging.getLogger(f"{__name__}.{name}")

    @abstractmethod
    def execute(self, task: Task) -> AgentResult:
        """
        Execute the given task.

        Args:
            task: The task to execute

        Returns:
            AgentResult containing execution results
        """
        pass

    def validate_input(self, input_str: str) -> bool:
        """
        Validate input before execution.

        Args:
            input_str: Input string to validate

        Returns:
            True if valid, False otherwise
        """
        if not input_str or len(input_str.strip()) == 0:
            return False
        if len(input_str) > self.config.get('max_input_length', 10000):
            return False
        return True

    def get_capabilities(self) -> List[str]:
        """
        Get list of agent capabilities.

        Returns:
            List of capability strings
        """
        return []

    def get_config(self) -> Dict[str, Any]:
        """
        Get agent configuration.

        Returns:
            Configuration dictionary
        """
        return {
            'name': self.name,
            'model': self.model,
            'max_iterations': self.max_iterations,
            'timeout': self.timeout,
            'capabilities': self.get_capabilities()
        }

    def log(self, level: int, message: str, **kwargs):
        """Log a message with additional context."""
        extra = {'agent': self.name, 'model': self.model}
        extra.update(kwargs)
        self._logger.log(level, message, extra=extra)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, model={self.model})"
