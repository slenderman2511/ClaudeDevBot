"""
Observability Module

Provides logging and tracing capabilities.
"""

from devbot.observability.logger import get_logger
from devbot.observability.tracing import setup_tracing

__all__ = ["get_logger", "setup_tracing"]
