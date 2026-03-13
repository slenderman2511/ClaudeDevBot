"""
Memory Module

Provides short-term and long-term memory for the AI DevBot.
- Short-term: Session context with TTL
- Long-term: Persistent storage with optional embeddings
"""

import os
import json
import time
import logging
import threading
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta
from pathlib import Path
from collections import OrderedDict

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """
    In-memory cache with TTL (Time To Live) for session context.

    Automatically evicts expired entries to prevent memory leaks.
    """

    def __init__(self, max_items: int = 100, default_ttl: int = 3600):
        """
        Initialize short-term memory.

        Args:
            max_items: Maximum number of items to store
            default_ttl: Default time-to-live in seconds (1 hour)
        """
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._max_items = max_items
        self._default_ttl = default_ttl
        self._lock = threading.Lock()

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Store a value in memory.

        Args:
            key: Memory key
            value: Value to store
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        with self._lock:
            ttl = ttl or self._default_ttl
            expires_at = time.time() + ttl

            self._cache[key] = {
                "value": value,
                "expires_at": expires_at,
                "created_at": time.time()
            }

            # Evict oldest if over limit
            while len(self._cache) > self._max_items:
                self._cache.popitem(last=False)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a value from memory.

        Args:
            key: Memory key
            default: Default value if key not found or expired

        Returns:
            Stored value or default
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                return default

            # Check expiration
            if time.time() > entry["expires_at"]:
                del self._cache[key]
                return default

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            return entry["value"]

    def delete(self, key: str) -> bool:
        """Delete a key from memory."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all memory."""
        with self._lock:
            self._cache.clear()

    def cleanup_expired(self) -> int:
        """Remove expired entries. Returns count of removed items."""
        with self._lock:
            now = time.time()
            expired_keys = [
                k for k, v in self._cache.items()
                if now > v["expires_at"]
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)

    def keys(self) -> List[str]:
        """Get all active (non-expired) keys."""
        with self._lock:
            self.cleanup_expired()
            return list(self._cache.keys())

    def __len__(self) -> int:
        """Get number of items in memory."""
        with self._lock:
            self.cleanup_expired()
            return len(self._cache)


class LongTermMemory:
    """
    Persistent memory with file-based storage.

    Stores project context, architecture notes, and learned patterns.
    """

    def __init__(self, storage_path: str = "data/memory/long_term"):
        """
        Initialize long-term memory.

        Args:
            storage_path: Directory for persistent storage
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Memory index
        self._index_file = self.storage_path / "index.json"
        self._index: Dict[str, Dict[str, Any]] = self._load_index()

    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        """Load memory index from disk."""
        if self._index_file.exists():
            try:
                return json.loads(self._index_file.read_text())
            except Exception as e:
                logger.error(f"Failed to load index: {e}")
        return {}

    def _save_index(self) -> None:
        """Save memory index to disk."""
        try:
            self._index_file.write_text(json.dumps(self._index, indent=2))
        except Exception as e:
            logger.error(f"Failed to save index: {e}")

    def store(self, key: str, value: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store a value in long-term memory.

        Args:
            key: Memory key
            value: Value to store (must be JSON serializable)
            metadata: Optional metadata

        Returns:
            True if stored successfully
        """
        try:
            # Create memory file
            safe_key = key.replace("/", "_").replace(" ", "_")
            memory_file = self.storage_path / f"{safe_key}.json"

            memory_data = {
                "key": key,
                "value": value,
                "metadata": metadata or {},
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }

            memory_file.write_text(json.dumps(memory_data, indent=2))

            # Update index
            self._index[key] = {
                "file": str(memory_file),
                "size": len(json.dumps(value)),
                "updated_at": memory_data["updated_at"]
            }
            self._save_index()

            logger.info(f"Stored in long-term memory: {key}")
            return True

        except Exception as e:
            logger.error(f"Failed to store memory {key}: {e}")
            return False

    def retrieve(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a value from long-term memory.

        Args:
            key: Memory key
            default: Default value if key not found

        Returns:
            Stored value or default
        """
        if key not in self._index:
            return default

        try:
            memory_file = Path(self._index[key]["file"])
            if memory_file.exists():
                data = json.loads(memory_file.read_text())
                return data.get("value", default)
        except Exception as e:
            logger.error(f"Failed to retrieve memory {key}: {e}")

        return default

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search memory by key pattern.

        Args:
            query: Search query (matches keys containing query)

        Returns:
            List of matching memory entries
        """
        results = []
        query_lower = query.lower()

        for key in self._index:
            if query_lower in key.lower():
                entry = self.retrieve(key)
                results.append({
                    "key": key,
                    "value": entry,
                    "metadata": self._index[key]
                })

        return results

    def delete(self, key: str) -> bool:
        """Delete a memory entry."""
        if key not in self._index:
            return False

        try:
            memory_file = Path(self._index[key]["file"])
            if memory_file.exists():
                memory_file.unlink()

            del self._index[key]
            self._save_index()
            return True
        except Exception as e:
            logger.error(f"Failed to delete memory {key}: {e}")
            return False

    def list_keys(self) -> List[str]:
        """List all memory keys."""
        return list(self._index.keys())

    def clear(self) -> None:
        """Clear all long-term memory."""
        for key in list(self._index.keys()):
            self.delete(key)


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
        self.long_term = LongTermMemory(long_term_path or "data/memory/long_term")

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


# Default instances
_short_term_memory: Optional[ShortTermMemory] = None
_long_term_memory: Optional[LongTermMemory] = None
_memory: Optional[Memory] = None


def get_short_term_memory() -> ShortTermMemory:
    """Get default short-term memory instance."""
    global _short_term_memory
    if _short_term_memory is None:
        _short_term_memory = ShortTermMemory()
    return _short_term_memory


def get_long_term_memory() -> LongTermMemory:
    """Get default long-term memory instance."""
    global _long_term_memory
    if _long_term_memory is None:
        _long_term_memory = LongTermMemory()
    return _long_term_memory


def get_memory() -> Memory:
    """Get default unified memory instance."""
    global _memory
    if _memory is None:
        _memory = Memory()
    return _memory
