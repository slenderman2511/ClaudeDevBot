"""
Long-Term Memory Module

Persistent memory with file-based storage.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from devbot.observability.logger import get_logger

logger = get_logger(__name__)


class LongTermMemory:
    """
    Persistent memory with file-based storage.

    Stores project context, architecture notes, and learned patterns.
    """

    def __init__(self, storage_path: str = ".devbot/memory"):
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
