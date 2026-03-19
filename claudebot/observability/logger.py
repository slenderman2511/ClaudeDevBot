"""
Logging Module

Provides structured logging for DevBot.
"""

import logging
import sys
from typing import Optional

# Default format
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(
    name: str,
    level: int = logging.INFO,
    format_str: Optional[str] = None,
    colorize: bool = True
) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name
        level: Logging level
        format_str: Custom format string
        colorize: Enable colorized output

    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)

    # Avoid adding multiple handlers
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # Format
    formatter_args = {
        "fmt": format_str or DEFAULT_FORMAT,
        "datefmt": DEFAULT_DATE_FORMAT
    }

    # Try to use colorlog if available
    try:
        import colorlog

        if colorize:
            formatter = colorlog.ColoredFormatter(
                "%(log_color)s" + (format_str or DEFAULT_FORMAT),
                datefmt=DEFAULT_DATE_FORMAT,
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            )
        else:
            formatter = logging.Formatter(**formatter_args)
    except ImportError:
        formatter = logging.Formatter(**formatter_args)

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def configure_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format_str: Optional[str] = None
) -> None:
    """
    Configure global logging settings.

    Args:
        level: Global logging level
        log_file: Optional file path for file logging
        format_str: Custom format string
    """
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(
        logging.Formatter(format_str or DEFAULT_FORMAT, DEFAULT_DATE_FORMAT)
    )
    root_logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(
            logging.Formatter(format_str or DEFAULT_FORMAT, DEFAULT_DATE_FORMAT)
        )
        root_logger.addHandler(file_handler)


class LogContext:
    """Context manager for temporary log level changes."""

    def __init__(self, logger: logging.Logger, level: int):
        self.logger = logger
        self.level = level
        self.original_level = logger.level

    def __enter__(self):
        self.logger.setLevel(self.level)
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.setLevel(self.original_level)
