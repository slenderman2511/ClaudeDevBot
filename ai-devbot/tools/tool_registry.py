"""
Tool Registry Module

Dynamic tool discovery and registration system.
Allows tools to be registered, discovered, and used dynamically.
"""

import logging
import importlib
import inspect
from typing import Any, Dict, List, Optional, Type, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """Tool categories for organization."""
    AI = "ai"           # Claude, OpenAI, etc.
    VERSION_CONTROL = "version_control"  # Git, SVN
    DEPLOYMENT = "deployment"  # Docker, K8s, Vercel
    TESTING = "testing"  # pytest, jest
    DATABASE = "database"  # SQL, migrations
    FILESYSTEM = "filesystem"  # File operations
    NETWORK = "network"  # HTTP, APIs
    UTILITY = "utility"  # Misc utilities


@dataclass
class ToolMetadata:
    """Metadata about a registered tool."""
    name: str
    category: ToolCategory
    description: str
    version: str
    capabilities: List[str]
    requires_auth: bool = False
    config_schema: Optional[Dict] = None


class ToolRegistry:
    """
    Registry for dynamic tool discovery and management.

    Provides:
    - Lazy loading of tools
    - Dynamic tool registration
    - Category-based organization
    - Tool capability matching
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the registry."""
        if not ToolRegistry._initialized:
            self._tools: Dict[str, Any] = {}
            self._metadata: Dict[str, ToolMetadata] = {}
            self._factories: Dict[str, Callable] = {}
            self._categories: Dict[ToolCategory, List[str]] = {
                category: [] for category in ToolCategory
            }
            self._initialized = True
            logger.info("ToolRegistry initialized")

    def register(
        self,
        name: str,
        tool_class: Type,
        category: ToolCategory,
        description: str = "",
        version: str = "1.0.0",
        capabilities: List[str] = None,
        factory: Optional[Callable] = None
    ) -> None:
        """
        Register a tool with the registry.

        Args:
            name: Tool name
            tool_class: Tool class
            category: Tool category
            description: Tool description
            version: Tool version
            capabilities: List of capabilities
            factory: Optional factory function for lazy instantiation
        """
        if name in self._tools:
            logger.warning(f"Tool {name} already registered, skipping")
            return

        metadata = ToolMetadata(
            name=name,
            category=category,
            description=description,
            version=version,
            capabilities=capabilities or []
        )

        self._tools[name] = tool_class
        self._metadata[name] = metadata
        self._categories[category].append(name)

        if factory:
            self._factories[name] = factory

        logger.info(f"Registered tool: {name} [{category.value}]")

    def register_lazy(self, name: str, module_path: str, class_name: str, **kwargs) -> None:
        """
        Register a tool with lazy loading.

        Args:
            name: Tool name
            module_path: Path to module (e.g., 'tools.git_tools')
            class_name: Class name in module
            **kwargs: Additional arguments for registration
        """
        def factory():
            """Lazy factory that imports and instantiates the tool."""
            module = importlib.import_module(module_path)
            tool_class = getattr(module, class_name)
            return tool_class

        self._factories[name] = factory
        # Store metadata but not the actual class
        kwargs['factory'] = factory
        # Use a placeholder for lazy registration
        self._tools[name] = None  # Will be loaded on first use

        # Create metadata
        metadata = ToolMetadata(
            name=name,
            category=kwargs.get('category', ToolCategory.UTILITY),
            description=kwargs.get('description', ''),
            version=kwargs.get('version', '1.0.0'),
            capabilities=kwargs.get('capabilities', [])
        )
        self._metadata[name] = metadata
        self._categories[kwargs.get('category', ToolCategory.UTILITY)].append(name)

        logger.info(f"Lazily registered tool: {name}")

    def get(self, name: str, config: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """
        Get a tool instance by name.

        Args:
            name: Tool name
            config: Optional configuration for tool instantiation

        Returns:
            Tool instance or None
        """
        if name not in self._tools:
            logger.warning(f"Tool not found: {name}")
            return None

        # Check for lazy factory
        if self._tools[name] is None and name in self._factories:
            try:
                self._tools[name] = self._factories[name]()
            except Exception as e:
                logger.error(f"Failed to load lazy tool {name}: {e}")
                return None

        tool_class = self._tools[name]

        # Instantiate if needed
        if inspect.isclass(tool_class):
            try:
                return tool_class(config) if config else tool_class()
            except Exception as e:
                logger.error(f"Failed to instantiate tool {name}: {e}")
                return None

        return tool_class

    def get_metadata(self, name: str) -> Optional[ToolMetadata]:
        """Get tool metadata."""
        return self._metadata.get(name)

    def list_tools(self, category: Optional[ToolCategory] = None) -> List[str]:
        """
        List all registered tools.

        Args:
            category: Optional category filter

        Returns:
            List of tool names
        """
        if category:
            return list(self._categories.get(category, []))
        return list(self._tools.keys())

    def find_tools(self, capability: str) -> List[str]:
        """
        Find tools that provide a specific capability.

        Args:
            capability: Capability to search for

        Returns:
            List of tool names with that capability
        """
        results = []
        for name, metadata in self._metadata.items():
            if capability.lower() in [c.lower() for c in metadata.capabilities]:
                results.append(name)
        return results

    def unregister(self, name: str) -> bool:
        """Unregister a tool."""
        if name not in self._tools:
            return False

        metadata = self._metadata.get(name)
        if metadata:
            category_tools = self._categories.get(metadata.category, [])
            if name in category_tools:
                category_tools.remove(name)

        del self._tools[name]
        del self._metadata[name]
        self._factories.pop(name, None)

        logger.info(f"Unregistered tool: {name}")
        return True

    def get_registry_summary(self) -> Dict[str, Any]:
        """Get summary of the registry."""
        return {
            'total_tools': len(self._tools),
            'by_category': {
                category.value: len(tools)
                for category, tools in self._categories.items()
                if tools
            },
            'lazy_tools': len(self._factories),
            'tools': list(self._metadata.keys())
        }


# Global registry instance
_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def register_tool(name: str, category: ToolCategory, **kwargs):
    """Convenience decorator for registering tools."""
    def decorator(tool_class):
        registry = get_registry()
        registry.register(name, tool_class, category, **kwargs)
        return tool_class
    return decorator


def discover_tools(base_module: str = "tools") -> int:
    """
    Auto-discover tools in a module.

    Looks for classes that inherit from Tool base class.

    Args:
        base_module: Base module to search

    Returns:
        Number of tools discovered
    """
    from tools.tool import Tool

    registry = get_registry()
    count = 0

    try:
        module = importlib.import_module(base_module)
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, Tool) and obj != Tool:
                # Try to determine category from class name
                category = ToolCategory.UTILITY
                if 'git' in name.lower():
                    category = ToolCategory.VERSION_CONTROL
                elif 'claude' in name.lower() or 'ai' in name.lower():
                    category = ToolCategory.AI
                elif 'deploy' in name.lower():
                    category = ToolCategory.DEPLOYMENT

                registry.register(
                    name=name,
                    tool_class=obj,
                    category=category,
                    description=obj.__doc__ or ""[:100] if obj.__doc__ else "",
                )
                count += 1
    except ImportError as e:
        logger.error(f"Failed to discover tools: {e}")

    return count
