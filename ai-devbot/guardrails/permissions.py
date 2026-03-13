"""
Permissions Module

Manages user permissions and access control.
"""

import logging
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class PermissionLevel(Enum):
    """User permission levels."""
    NONE = 0
    READ = 1
    WRITE = 2
    EXECUTE = 3
    ADMIN = 4


@dataclass
class User:
    """Represents a user with permissions."""
    user_id: int
    username: str
    permission_level: PermissionLevel = PermissionLevel.NONE
    allowed_commands: List[str] = None
    blocked: bool = False

    def __post_init__(self):
        if self.allowed_commands is None:
            self.allowed_commands = []


class PermissionManager:
    """
    Manages user permissions and access control.

    Controls which users can access which commands.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize permission manager.

        Args:
            config: Permission configuration
        """
        self.config = config or {}
        self._users: Dict[int, User] = {}
        self._allowed_users: Set[int] = set(self.config.get('allowed_users', []))
        self._default_permission = PermissionLevel[self.config.get('default_permission', 'READ').upper()]
        self._default_commands = self.config.get('default_commands', [])
        self._logger = logging.getLogger(__name__)

    def add_user(self, user_id: int, username: str, permission_level: PermissionLevel = None):
        """
        Add a user.

        Args:
            user_id: Telegram user ID
            username: Username
            permission_level: Permission level
        """
        if permission_level is None:
            permission_level = self._default_permission

        user = User(
            user_id=user_id,
            username=username,
            permission_level=permission_level,
            allowed_commands=self._default_commands.copy()
        )
        self._users[user_id] = user
        logger.info(f"Added user: {username} (ID: {user_id})")

    def remove_user(self, user_id: int):
        """Remove a user."""
        if user_id in self._users:
            del self._users[user_id]
            logger.info(f"Removed user: {user_id}")

    def block_user(self, user_id: int):
        """Block a user."""
        if user_id in self._users:
            self._users[user_id].blocked = True
            logger.info(f"Blocked user: {user_id}")

    def unblock_user(self, user_id: int):
        """Unblock a user."""
        if user_id in self._users:
            self._users[user_id].blocked = False
            logger.info(f"Unblocked user: {user_id}")

    def is_allowed(self, user_id: int) -> bool:
        """
        Check if a user is allowed to use the bot.

        Args:
            user_id: Telegram user ID

        Returns:
            True if allowed
        """
        # Allow if user list is empty (no restriction)
        if not self._allowed_users:
            return True

        return user_id in self._allowed_users

    def can_execute_command(self, user_id: int, command: str) -> bool:
        """
        Check if a user can execute a command.

        Args:
            user_id: Telegram user ID
            command: Command to check

        Returns:
            True if allowed
        """
        # Check if user is blocked
        if user_id in self._users and self._users[user_id].blocked:
            return False

        # Check if user is allowed at all
        if not self.is_allowed(user_id):
            return False

        # Check specific command permission
        if user_id in self._users:
            user = self._users[user_id]
            if user.allowed_commands:
                return command in user.allowed_commands

        # Default: allow if not in blocked list
        return True

    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self._users.get(user_id)

    def list_users(self) -> List[User]:
        """List all users."""
        return list(self._users.values())

    def set_user_permission(self, user_id: int, permission_level: PermissionLevel):
        """Set user permission level."""
        if user_id in self._users:
            self._users[user_id].permission_level = permission_level

    def add_user_command(self, user_id: int, command: str):
        """Add a command to user's allowed list."""
        if user_id in self._users:
            if command not in self._users[user_id].allowed_commands:
                self._users[user_id].allowed_commands.append(command)
