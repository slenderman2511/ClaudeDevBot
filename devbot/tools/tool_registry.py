"""
Tool Registry Module

Central registry for all available tools.
"""

from typing import Dict, List, Optional, Any

from devbot.tools.tool import Tool
from devbot.observability.logger import get_logger

logger = get_logger(__name__)


class ToolRegistry:
    """
    Central registry for all available tools.

    Provides registration, lookup, and management of tools.
    """

    def __init__(self):
        """Initialize the tool registry."""
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """
        Register a tool.

        Args:
            tool: Tool instance to register
        """
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def unregister(self, name: str) -> bool:
        """
        Unregister a tool.

        Args:
            name: Tool name

        Returns:
            True if tool was unregistered
        """
        if name in self._tools:
            del self._tools[name]
            logger.info(f"Unregistered tool: {name}")
            return True
        return False

    def get(self, name: str) -> Optional[Tool]:
        """
        Get a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        """
        List all registered tool names.

        Returns:
            List of tool names
        """
        return list(self._tools.keys())

    def get_all(self) -> Dict[str, Tool]:
        """
        Get all registered tools.

        Returns:
            Dictionary of tools
        """
        return self._tools.copy()

    def execute(self, tool_name: str, **kwargs) -> Any:
        """
        Execute a tool by name.

        Args:
            tool_name: Name of tool to execute
            **kwargs: Arguments for tool execution

        Returns:
            Tool execution result
        """
        tool = self.get(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")

        return tool.execute(**kwargs)

    def validate(self, name: str) -> bool:
        """
        Validate a tool.

        Args:
            name: Tool name

        Returns:
            True if tool is valid
        """
        tool = self.get(name)
        if not tool:
            return False
        return tool.validate()

    def get_schemas(self) -> List[Dict[str, Any]]:
        """
        Get schemas for all registered tools.

        Returns:
            List of tool schemas
        """
        return [tool.get_schema() for tool in self._tools.values()]


# Global registry instance
_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """Get the global tool registry."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def register_tool(tool: Tool) -> None:
    """Register a tool with the global registry."""
    get_registry().register(tool)


def get_tool(name: str) -> Optional[Tool]:
    """Get a tool from the global registry."""
    return get_registry().get(name)
