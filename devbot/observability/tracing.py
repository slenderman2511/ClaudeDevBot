"""
Tracing Module

Provides tracing capabilities for DevBot operations.
"""

import time
import functools
from typing import Optional, Callable, Any, Dict
from contextlib import contextmanager

from devbot.observability.logger import get_logger

logger = get_logger(__name__)


class Tracer:
    """Simple tracer for tracking operation execution."""

    def __init__(self, name: str = "devbot"):
        self.name = name
        self._spans: Dict[str, dict] = {}

    @contextmanager
    def span(self, operation_name: str, **attributes):
        """
        Context manager for tracing an operation.

        Args:
            operation_name: Name of the operation
            **attributes: Additional attributes to track

        Example:
            with tracer.span("scan_project"):
                # do work
                pass
        """
        span_id = f"{operation_name}_{int(time.time() * 1000)}"
        start_time = time.time()

        logger.debug(f"Starting: {operation_name}", extra={"span_id": span_id})

        try:
            yield span_id
        finally:
            duration = time.time() - start_time
            self._spans[span_id] = {
                "operation": operation_name,
                "duration": duration,
                "attributes": attributes
            }
            logger.debug(
                f"Completed: {operation_name} in {duration:.3f}s",
                extra={"span_id": span_id, "duration": duration}
            )

    def trace(self, operation_name: str = None) -> Callable:
        """
        Decorator for tracing function execution.

        Args:
            operation_name: Name of the operation (defaults to function name)

        Example:
            @tracer.trace()
            def my_function():
                pass
        """
        def decorator(func: Callable) -> Callable:
            name = operation_name or func.__name__

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                with self.span(name, function=func.__name__):
                    return func(*args, **kwargs)

            return wrapper
        return decorator

    def get_spans(self) -> Dict[str, dict]:
        """Get all recorded spans."""
        return self._spans.copy()

    def clear_spans(self):
        """Clear all recorded spans."""
        self._spans.clear()


# Global tracer instance
_tracer: Optional[Tracer] = None


def get_tracer(name: str = "devbot") -> Tracer:
    """Get the global tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = Tracer(name)
    return _tracer


def setup_tracing(enabled: bool = True) -> None:
    """
    Setup tracing for DevBot.

    Args:
        enabled: Whether tracing is enabled
    """
    if enabled:
        logger.info("Tracing enabled")
    else:
        logger.info("Tracing disabled")


# Convenience decorators
trace = get_tracer().trace
span = get_tracer().span
