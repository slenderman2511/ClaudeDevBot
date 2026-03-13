"""
Command Router Module

Routes Telegram commands to appropriate handlers and agents.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class CommandType(Enum):
    """Supported command types."""
    SPEC = "spec"
    CODE = "code"
    TEST = "test"
    DEPLOY = "deploy"
    DEBUG = "debug"
    STATUS = "status"
    HELP = "help"
    UNKNOWN = "unknown"


@dataclass
class ParsedCommand:
    """Represents a parsed command from Telegram."""
    command_type: CommandType
    raw_command: str
    arguments: str
    user_id: int
    chat_id: int
    message_id: int


class CommandRouter:
    """
    Routes incoming Telegram commands to appropriate agents and handlers.

    Parses command text and routes to the correct agent type.
    """

    # Command patterns
    COMMAND_PATTERNS = {
        CommandType.SPEC: r'^/spec\s*(.*)$',
        CommandType.CODE: r'^/code\s*(.*)$',
        CommandType.TEST: r'^/test\s*(.*)$',
        CommandType.DEPLOY: r'^/deploy\s*(.*)$',
        CommandType.DEBUG: r'^/debug\s*(.*)$',
        CommandType.STATUS: r'^/status\s*$',
        CommandType.HELP: r'^/help\s*$',
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the command router.

        Args:
            config: Router configuration
        """
        self.config = config or {}
        self._handlers: Dict[CommandType, Callable] = {}
        self._logger = logging.getLogger(__name__)

    def register_handler(self, command_type: CommandType, handler: Callable):
        """Register a handler for a command type."""
        self._handlers[command_type] = handler

    def parse_command(self, text: str, user_id: int, chat_id: int, message_id: int) -> ParsedCommand:
        """
        Parse a command from Telegram message.

        Args:
            text: Message text
            user_id: User ID
            chat_id: Chat ID
            message_id: Message ID

        Returns:
            ParsedCommand object
        """
        text = text.strip()

        for cmd_type, pattern in self.COMMAND_PATTERNS.items():
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                arguments = match.group(1).strip() if match.lastindex and match.lastindex >= 1 else ""
                self._logger.info(f"Parsed command: {cmd_type.value} with args: {arguments[:50]}...")

                return ParsedCommand(
                    command_type=cmd_type,
                    raw_command=text,
                    arguments=arguments,
                    user_id=user_id,
                    chat_id=chat_id,
                    message_id=message_id
                )

        # Unknown command
        return ParsedCommand(
            command_type=CommandType.UNKNOWN,
            raw_command=text,
            arguments="",
            user_id=user_id,
            chat_id=chat_id,
            message_id=message_id
        )

    def route(self, parsed_command: ParsedCommand) -> Any:
        """
        Route a parsed command to its handler.

        Args:
            parsed_command: Parsed command to route

        Returns:
            Handler result

        Raises:
            ValueError: If no handler is registered
        """
        handler = self._handlers.get(parsed_command.command_type)

        if handler is None:
            # Return default response
            return self._get_default_response(parsed_command)

        return handler(parsed_command)

    def _get_default_response(self, parsed_command: ParsedCommand) -> str:
        """Get default response for a command."""
        if parsed_command.command_type == CommandType.UNKNOWN:
            return "Unknown command. Use /help to see available commands."
        return f"Command {parsed_command.command_type.value} not configured."

    def get_help_text(self) -> str:
        """Get help text for all commands."""
        return """
AI DevBot Commands:

/spec <description> - Generate a specification document
/code <requirement> - Generate implementation code
/test <scope> - Run tests
/deploy <target> - Deploy to target
/debug <error> - Analyze and debug issues
/status - Show system status
/help - Show this help message
        """.strip()

    def get_command_mapping(self) -> Dict[str, str]:
        """Get mapping of command strings to descriptions."""
        return {
            "/spec": "Generate specification document",
            "/code": "Generate implementation code",
            "/test": "Run tests",
            "/deploy": "Deploy service",
            "/debug": "Debug issues",
            "/status": "Check system status",
            "/help": "Show help"
        }
