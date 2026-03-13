"""
Memory Module

Unified memory interface combining short-term and long-term memory.
"""

from typing import Any, Dict, Optional, List

from devbot.memory.short_term_memory import ShortTermMemory
from devbot.memory.long_term_memory import LongTermMemory


class Memory:
    """
    Unified memory interface combining short-term and long-term memory.

    Provides a seamless API for both memory types.
    """

    def __init__(self, short_term_config: Optional[Dict[str, Any]] = None, long_term_path: Optional[str] = None):
        """
        Initialize memory system.

        Args:
            short_term_config: Configuration for short-term memory
            long_term_path: Path for long-term storage
        """
        short_term_config = short_term_config or {}
        self.short_term = ShortTermMemory(
            max_items=short_term_config.get("max_items", 100),
            default_ttl=short_term_config.get("ttl_seconds", 3600)
        )
        self.long_term = LongTermMemory(long_term_path or ".devbot/memory")

    def set(self, key: str, value: Any, long_term: bool = False, ttl: Optional[int] = None) -> bool:
        """
        Store a value in memory.

        Args:
            key: Memory key
            value: Value to store
            long_term: If True, store in long-term memory
            ttl: Time-to-live for short-term memory

        Returns:
            True if stored successfully
        """
        if long_term:
            return self.long_term.store(key, value)
        else:
            self.short_term.set(key, value, ttl)
            return True

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a value from memory.

        Checks short-term first, then long-term.

        Args:
            key: Memory key
            default: Default value if not found

        Returns:
            Stored value or default
        """
        # Try short-term first
        value = self.short_term.get(key)
        if value is not None:
            return value

        # Fall back to long-term
        return self.long_term.retrieve(key, default)

    def remember(self, key: str, value: Any) -> bool:
        """Shortcut to store in both short-term and long-term."""
        self.short_term.set(key, value)
        return self.long_term.store(key, value)

    def forget(self, key: str) -> bool:
        """Remove from both short-term and long-term memory."""
        self.short_term.delete(key)
        return self.long_term.delete(key)

    def clear_short_term(self) -> None:
        """Clear short-term memory."""
        self.short_term.clear()

    def clear_all(self) -> None:
        """Clear all memory."""
        self.short_term.clear()
        self.long_term.clear()


# Default instance
_memory: Optional[Memory] = None


def get_memory() -> Memory:
    """Get default unified memory instance."""
    global _memory
    if _memory is None:
        _memory = Memory()
    return _memory
