"""
Logging Module

Provides structured JSON logging for the AI DevBot system.
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from logging.handlers import RotatingFileHandler


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # Add extra fields
        if hasattr(record, 'agent'):
            log_data['agent'] = record.agent
        if hasattr(record, 'model'):
            log_data['model'] = record.model
        if hasattr(record, 'workflow_id'):
            log_data['workflow_id'] = record.workflow_id

        # Add exception info
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class Logger:
    """
    Structured logger for AI DevBot.

    Provides convenient methods for different log levels.
    """

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize logger.

        Args:
            name: Logger name
            config: Logging configuration
        """
        self.config = config or {}
        self._logger = logging.getLogger(name)
        self._setup_logger()

    def _setup_logger(self):
        """Setup logger with handlers and formatters."""
        if self._logger.handlers:
            return

        level = self.config.get('level', 'INFO')
        self._logger.setLevel(getattr(logging, level))

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)

        # Use JSON formatter for production, simple for dev
        if self.config.get('format') == 'json':
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)

        # File handler if configured
        if 'file_path' in self.config:
            file_handler = RotatingFileHandler(
                self.config['file_path'],
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs):
        """Log info message."""
        self._logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs):
        """Log error message."""
        self._logger.error(message, extra=kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self._logger.critical(message, extra=kwargs)

    def exception(self, message: str, **kwargs):
        """Log exception with traceback."""
        self._logger.exception(message, extra=kwargs)


def get_logger(name: str, config: Optional[Dict[str, Any]] = None) -> Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name
        config: Logging configuration

    Returns:
        Logger instance
    """
    return Logger(name, config)


# Default logger configuration
DEFAULT_CONFIG = {
    'level': 'INFO',
    'format': 'text',
    'output': 'stdout'
}
