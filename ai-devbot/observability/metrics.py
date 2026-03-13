"""
Metrics Module

Provides metrics collection for the AI DevBot system.
"""

import logging
import time
from typing import Any, Dict, Optional
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


@dataclass
class Counter:
    """Metric counter."""
    name: str
    value: int = 0
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Gauge:
    """Metric gauge."""
    name: str
    value: float = 0.0
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class Histogram:
    """Metric histogram."""
    name: str
    buckets: Dict[float, int] = field(default_factory=dict)
    sum: float = 0.0
    count: int = 0
    labels: Dict[str, str] = field(default_factory=dict)


class Metrics:
    """
    Metrics collector for AI DevBot.

    Provides counters, gauges, and histograms for monitoring.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize metrics.

        Args:
            config: Metrics configuration
        """
        self.config = config or {}
        self.enabled = self.config.get('enabled', True)
        self.port = self.config.get('port', 9090)

        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._lock = threading.Lock()

    def counter(self, name: str, labels: Optional[Dict[str, str]] = None, value: int = 1):
        """
        Increment a counter.

        Args:
            name: Counter name
            labels: Labels for the counter
            value: Value to increment by
        """
        if not self.enabled:
            return

        key = self._make_key(name, labels)
        with self._lock:
            if key not in self._counters:
                self._counters[key] = Counter(name=name, labels=labels or {})
            self._counters[key].value += value

    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """
        Set a gauge value.

        Args:
            name: Gauge name
            value: Value to set
            labels: Labels for the gauge
        """
        if not self.enabled:
            return

        key = self._make_key(name, labels)
        with self._lock:
            if key not in self._gauges:
                self._gauges[key] = Gauge(name=name, labels=labels or {})
            self._gauges[key].value = value

    def histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """
        Record a histogram value.

        Args:
            name: Histogram name
            value: Value to record
            labels: Labels for the histogram
        """
        if not self.enabled:
            return

        key = self._make_key(name, labels)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = Histogram(name=name, labels=labels or {})

            hist = self._histograms[key]
            hist.sum += value
            hist.count += 1

            # Update buckets
            for bucket in [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]:
                if value <= bucket:
                    hist.buckets[bucket] = hist.buckets.get(bucket, 0) + 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics."""
        with self._lock:
            return {
                'counters': {k: {'value': v.value, 'labels': v.labels}
                           for k, v in self._counters.items()},
                'gauges': {k: {'value': v.value, 'labels': v.labels}
                          for k, v in self._gauges.items()},
                'histograms': {k: {'count': v.count, 'sum': v.sum, 'labels': v.labels}
                              for k, v in self._histograms.items()}
            }

    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Create a unique key for a metric."""
        if not labels:
            return name
        label_str = ','.join(f'{k}={v}' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"


# Common metric names
class MetricNames:
    """Standard metric names."""
    # Agent metrics
    AGENT_EXECUTIONS = "ai_devbot_agent_executions_total"
    AGENT_DURATION = "ai_devbot_agent_duration_seconds"
    AGENT_ERRORS = "ai_devbot_agent_errors_total"

    # Workflow metrics
    WORKFLOW_EXECUTIONS = "ai_devbot_workflow_executions_total"
    WORKFLOW_DURATION = "ai_devbot_workflow_duration_seconds"
    WORKFLOW_ERRORS = "ai_devbot_workflow_errors_total"

    # Command metrics
    COMMANDS_RECEIVED = "ai_devbot_commands_received_total"
    COMMANDS_PROCESSED = "ai_devbot_commands_processed_total"

    # Tool metrics
    TOOL_EXECUTIONS = "ai_devbot_tool_executions_total"
    TOOL_DURATION = "ai_devbot_tool_duration_seconds"


# Global metrics instance
_global_metrics: Optional[Metrics] = None


def get_metrics(config: Optional[Dict[str, Any]] = None) -> Metrics:
    """
    Get the global metrics instance.

    Args:
        config: Metrics configuration

    Returns:
        Metrics instance
    """
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = Metrics(config)
    return _global_metrics
