"""
Event Bus Module

Pub/Sub event bus for event-driven architecture.
"""

import logging
import uuid
import threading
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
from events.event_types import Event, EventType

logger = logging.getLogger(__name__)


@dataclass
class EventHandler:
    """Represents an event handler."""

    callback: Callable
    event_type: EventType
    handler_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    enabled: bool = True


class EventBus:
    """
    Event bus for pub/sub messaging.

    Allows components to publish and subscribe to events.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the event bus."""
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._handlers: Dict[EventType, List[EventHandler]] = defaultdict(list)
        self._global_handlers: List[EventHandler] = []
        self._event_history: List[Event] = []
        self._history_size = 1000
        self._lock = threading.Lock()

        self._initialized = True
        logger.info("EventBus initialized")

    def subscribe(
        self,
        event_type: EventType,
        callback: Callable[[Event], None],
        description: str = ""
    ) -> str:
        """
        Subscribe to a specific event type.

        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event is published
            description: Description of the handler

        Returns:
            Handler ID for unsubscribing
        """
        handler = EventHandler(
            callback=callback,
            event_type=event_type,
            description=description
        )

        with self._lock:
            self._handlers[event_type].append(handler)

        logger.debug(f"Subscribed to {event_type.value}: {description}")
        return handler.handler_id

    def subscribe_all(self, callback: Callable[[Event], None], description: str = "") -> str:
        """
        Subscribe to all events.

        Args:
            callback: Function to call for any event
            description: Description of the handler

        Returns:
            Handler ID for unsubscribing
        """
        handler = EventHandler(
            callback=callback,
            event_type=EventType.SYSTEM_READY,  # Dummy type for global
            description=description
        )

        with self._lock:
            self._global_handlers.append(handler)

        logger.debug(f"Subscribed to all events: {description}")
        return handler.handler_id

    def unsubscribe(self, handler_id: str) -> bool:
        """
        Unsubscribe a handler.

        Args:
            handler_id: ID of handler to remove

        Returns:
            True if handler was found and removed
        """
        with self._lock:
            # Check specific handlers
            for event_type, handlers in self._handlers.items():
                for i, handler in enumerate(handlers):
                    if handler.handler_id == handler_id:
                        del handlers[i]
                        logger.debug(f"Unsubscribed handler {handler_id}")
                        return True

            # Check global handlers
            for i, handler in enumerate(self._global_handlers):
                if handler.handler_id == handler_id:
                    del self._global_handlers[i]
                    logger.debug(f"Unsubscribed global handler {handler_id}")
                    return True

        return False

    def publish(self, event: Event) -> int:
        """
        Publish an event to all subscribers.

        Args:
            event: Event to publish

        Returns:
            Number of handlers that received the event
        """
        # Add correlation ID if not present
        if not event.correlation_id:
            event.correlation_id = str(uuid.uuid4())[:8]

        # Store in history
        with self._lock:
            self._event_history.append(event)
            if len(self._event_history) > self._history_size:
                self._event_history = self._event_history[-self._history_size:]

        handler_count = 0

        # Notify specific handlers
        with self._lock:
            handlers = list(self._handlers.get(event.type, []))
            global_handlers = list(self._global_handlers)

        # Call specific handlers
        for handler in handlers:
            if handler.enabled:
                try:
                    handler.callback(event)
                    handler_count += 1
                except Exception as e:
                    logger.error(f"Handler {handler.handler_id} error: {e}")

        # Call global handlers
        for handler in global_handlers:
            if handler.enabled:
                try:
                    handler.callback(event)
                    handler_count += 1
                except Exception as e:
                    logger.error(f"Global handler {handler.handler_id} error: {e}")

        # Log event
        logger.debug(f"Published {event.type.value} to {handler_count} handlers")

        return handler_count

    def publish_sync(self, event: Event) -> int:
        """Synchronous publish (alias for publish)."""
        return self.publish(event)

    async def publish_async(self, event: Event) -> int:
        """Asynchronous publish."""
        return self.publish(event)

    def get_handlers(self, event_type: EventType) -> List[EventHandler]:
        """Get all handlers for an event type."""
        with self._lock:
            return list(self._handlers.get(event_type, []))

    def get_event_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 100
    ) -> List[Event]:
        """Get event history."""
        with self._lock:
            events = list(self._event_history)

        if event_type:
            events = [e for e in events if e.type == event_type]

        return events[-limit:]

    def clear_history(self):
        """Clear event history."""
        with self._lock:
            self._event_history.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        with self._lock:
            total_handlers = sum(len(h) for h in self._handlers.values())
            total_handlers += len(self._global_handlers)

            event_counts = {}
            for event in self._event_history:
                event_type = event.type.value
                event_counts[event_type] = event_counts.get(event_type, 0) + 1

            return {
                "total_handlers": total_handlers,
                "specific_handlers": sum(len(h) for h in self._handlers.values()),
                "global_handlers": len(self._global_handlers),
                "event_history_size": len(self._event_history),
                "event_counts": event_counts
            }


# Global event bus instance
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def publish(event: Event) -> int:
    """Convenience function to publish an event."""
    return get_event_bus().publish(event)


def subscribe(event_type: EventType, callback: Callable, description: str = "") -> str:
    """Convenience function to subscribe to an event."""
    return get_event_bus().subscribe(event_type, callback, description)
