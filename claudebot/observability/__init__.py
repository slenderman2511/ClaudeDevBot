"""
Observability Module

Provides logging and tracing capabilities.
"""

from claudebot.observability.logger import get_logger
from claudebot.observability.tracing import setup_tracing

__all__ = ["get_logger", "setup_tracing"]
