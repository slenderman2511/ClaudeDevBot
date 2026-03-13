"""
Tracing Module

Provides distributed tracing for the AI DevBot system.
"""

import logging
import time
import uuid
from typing import Any, Dict, Optional
from datetime import datetime
from contextlib import contextmanager
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Span:
    """Represents a trace span."""
    span_id: str
    trace_id: str
    parent_id: Optional[str]
    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: list = field(default_factory=list)
    status: str = "ok"  # ok, error


class Tracer:
    """
    Distributed tracer for AI DevBot.

    Provides span creation and management for distributed tracing.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize tracer.

        Args:
            config: Tracing configuration
        """
        self.config = config or {}
        self.service_name = self.config.get('service_name', 'ai-devbot')
        self.enabled = self.config.get('enabled', True)
        self.exporter = self.config.get('exporter', 'console')
        self._current_span: Optional[Span] = None
        self._spans: Dict[str, Span] = {}

    @contextmanager
    def start_span(self, operation_name: str, tags: Optional[Dict[str, Any]] = None):
        """
        Start a new span.

        Args:
            operation_name: Name of the operation
            tags: Optional tags for the span

        Yields:
            Span object
        """
        if not self.enabled:
            yield None
            return

        trace_id = self._current_span.trace_id if self._current_span else str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        parent_id = self._current_span.span_id if self._current_span else None

        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            parent_id=parent_id,
            operation_name=operation_name,
            start_time=time.time(),
            tags=tags or {}
        )

        previous_span = self._current_span
        self._current_span = span

        try:
            yield span
        except Exception as e:
            span.status = "error"
            span.tags['error'] = str(e)
            raise
        finally:
            span.end_time = time.time()
            self._spans[span_id] = span
            self._current_span = previous_span

            # Export span
            if self.exporter == 'console':
                self._export_console(span)

    def _export_console(self, span: Span):
        """Export span to console."""
        duration = span.end_time - span.start_time if span.end_time else 0
        logger.info(
            f"[TRACE] {span.operation_name} - "
            f"trace_id={span.trace_id} "
            f"span_id={span.span_id[:8]}... "
            f"duration={duration:.3f}s "
            f"status={span.status}"
        )

    def get_span(self, span_id: str) -> Optional[Span]:
        """Get a span by ID."""
        return self._spans.get(span_id)

    def get_current_span(self) -> Optional[Span]:
        """Get the current span."""
        return self._current_span


# Global tracer instance
_global_tracer: Optional[Tracer] = None


def get_tracer(config: Optional[Dict[str, Any]] = None) -> Tracer:
    """
    Get the global tracer instance.

    Args:
        config: Tracer configuration

    Returns:
        Tracer instance
    """
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = Tracer(config)
    return _global_tracer
