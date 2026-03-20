# .claudebot/agents/base_agent.py
"""Base agent class and interfaces"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


@dataclass
class AgentContext:
    """Context passed to all agents"""
    repo_path: str
    branch: str
    claude_api_key: str
    config: dict


@dataclass
class AgentResult:
    """Standard result from any agent"""
    success: bool
    summary: str
    files_created: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    error: Optional[str] = None


class BaseAgent(ABC):
    """Abstract base class for all agents"""

    name: str = "base"
    description: str = "Base agent"

    @abstractmethod
    async def execute(self, task: dict, context: AgentContext) -> AgentResult:
        """Execute the agent task. Returns result with files and logs."""
        pass

    @abstractmethod
    def validate_input(self, task: dict) -> tuple[bool, Optional[str]]:
        """Validate task input. Returns (is_valid, error_message)"""
        pass

    def get_required_files(self, task: dict) -> List[str]:
        """Return list of files agent needs to read"""
        return []

    async def on_error(self, error: Exception, task: dict) -> AgentResult:
        """Handle errors - can be overridden for custom recovery"""
        logger.exception(f"Agent {self.name} error: {error}")
        return AgentResult(
            success=False,
            summary=f"Error: {str(error)}",
            error=str(error)
        )
