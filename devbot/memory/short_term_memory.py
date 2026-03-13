"""
Short-Term Memory Module

In-memory cache with TTL (Time To Live) for session context.
"""

import time
import threading
from typing import Any, Optional
from collections import OrderedDict

from devbot.observability.logger import get_logger

logger = get_logger(__name__)


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
        self._cache: OrderedDict[str, dict] = OrderedDict()
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

    def keys(self) -> list:
        """Get all active (non-expired) keys."""
        with self._lock:
            self.cleanup_expired()
            return list(self._cache.keys())

    def __len__(self) -> int:
        """Get number of items in memory."""
        with self._lock:
            self.cleanup_expired()
            return len(self._cache)
