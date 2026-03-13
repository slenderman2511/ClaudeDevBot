"""
Tool Interface Module

Defines the abstract Tool class that all tools inherit from.
Provides a common interface for LLM tool usage.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Represents the result of tool execution."""
    success: bool
    output: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class Tool(ABC):
    """
    Abstract base class for all tools.

    All tools must inherit from this class and implement
    the execute method.
    """

    def __init__(
        self,
        name: str,
        description: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the tool.

        Args:
            name: Tool name identifier
            description: Tool description for LLM context
            config: Additional configuration
        """
        self.name = name
        self.description = description
        self.config = config or {}
        self._logger = logging.getLogger(f"{__name__}.{name}")

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given arguments.

        Args:
            **kwargs: Tool-specific arguments

        Returns:
            ToolResult containing execution results
        """
        pass

    def validate(self) -> bool:
        """
        Validate tool is properly configured.

        Returns:
            True if valid, False otherwise
        """
        return True

    def get_schema(self) -> Dict[str, Any]:
        """
        Get tool input schema for LLM function calling.

        Returns:
            JSON schema for tool inputs
        """
        return {
            'name': self.name,
            'description': self.description,
            'parameters': {
                'type': 'object',
                'properties': {},
                'required': []
            }
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name})"
