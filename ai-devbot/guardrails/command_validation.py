"""
Command Validation Module

Validates and sanitizes incoming commands.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of command validation."""
    is_valid: bool
    sanitized_input: str
    error_message: Optional[str] = None


class CommandValidator:
    """
    Validates and sanitizes incoming commands.

    Provides input validation and security checks.
    """

    # Dangerous patterns to block
    DANGEROUS_PATTERNS = [
        r'rm\s+-rf\s+/',
        r'DROP\s+DATABASE',
        r'DROP\s+TABLE',
        r'delete\s+from\s+\w+',
        r'--\s*\$',
        r';\s*rm\s',
        r'sudo\s+rm',
        r'>\s*/dev/sd',
        r'format\s+\w+:',
    ]

    # Suspicious patterns to warn
    SUSPICIOUS_PATTERNS = [
        r'exec\s*\(',
        r'eval\s*\(',
        r'__import__',
        r'subprocess',
        r'os\.system',
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize command validator.

        Args:
            config: Validator configuration
        """
        self.config = config or {}
        self.max_length = self.config.get('max_length', 1000)
        self.max_args = self.config.get('max_args', 20)
        self.allowed_commands = self.config.get('allowed_commands', [
            'spec', 'code', 'test', 'deploy', 'debug', 'status', 'help'
        ])
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns."""
        self._dangerous_regexes = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.DANGEROUS_PATTERNS
        ]
        self._suspicious_regexes = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.SUSPICIOUS_PATTERNS
        ]

    def validate(self, command: str, args: str) -> ValidationResult:
        """
        Validate a command.

        Args:
            command: Command string
            args: Arguments string

        Returns:
            ValidationResult
        """
        # Check command is allowed
        if command not in self.allowed_commands:
            return ValidationResult(
                is_valid=False,
                sanitized_input="",
                error_message=f"Command '{command}' is not allowed"
            )

        # Combine for validation
        full_input = f"{command} {args}".strip()

        # Check length
        if len(full_input) > self.max_length:
            return ValidationResult(
                is_valid=False,
                sanitized_input="",
                error_message=f"Input too long (max {self.max_length} characters)"
            )

        # Check for dangerous patterns
        for regex in self._dangerous_regexes:
            if regex.search(full_input):
                logger.warning(f"Dangerous pattern detected: {full_input[:50]}...")
                return ValidationResult(
                    is_valid=False,
                    sanitized_input="",
                    error_message="Command contains forbidden patterns"
                )

        # Sanitize input
        sanitized = self._sanitize(args)

        return ValidationResult(
            is_valid=True,
            sanitized_input=sanitized
        )

    def _sanitize(self, input_str: str) -> str:
        """
        Sanitize input string.

        Args:
            input_str: Input to sanitize

        Returns:
            Sanitized string
        """
        # Remove null bytes
        sanitized = input_str.replace('\x00', '')

        # Remove control characters except newlines and tabs
        sanitized = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', sanitized)

        # Trim whitespace
        sanitized = sanitized.strip()

        # Limit length
        if len(sanitized) > self.max_length:
            sanitized = sanitized[:self.max_length]

        return sanitized

    def check_suspicious(self, input_str: str) -> List[str]:
        """
        Check for suspicious patterns.

        Args:
            input_str: Input to check

        Returns:
            List of suspicious patterns found
        """
        found = []
        for regex in self._suspicious_regexes:
            if regex.search(input_str):
                found.append(regex.pattern)
        return found

    def validate_file_path(self, path: str) -> bool:
        """
        Validate a file path.

        Args:
            path: File path to validate

        Returns:
            True if valid
        """
        # Check for path traversal
        if '..' in path or path.startswith('/'):
            return False

        # Check for dangerous paths
        dangerous_paths = ['/etc/', '/usr/bin/', '/usr/sbin/', '/bin/', '/sbin/']
        for dp in dangerous_paths:
            if path.startswith(dp):
                return False

        return True
