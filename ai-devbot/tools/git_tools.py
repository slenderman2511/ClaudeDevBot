"""
Git Tools Module

Wrapper for Git operations.
"""

import subprocess
import logging
from typing import Any, Dict, Optional, List
from tools.tool import Tool, ToolResult

logger = logging.getLogger(__name__)


class GitTool(Tool):
    """
    Tool for executing Git operations.

    Provides capabilities for git status, commit, push, pull, and branch operations.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            name="git",
            description="Execute Git operations for version control",
            config=config or {}
        )
        self.default_branch = self.config.get('default_branch', 'main')
        self.commit_prefix = self.config.get('commit_message_prefix', '[AI-DevBot]')

    def execute(self, command: str, **kwargs) -> ToolResult:
        """
        Execute a Git command.

        Args:
            command: Git subcommand (e.g., 'status', 'commit', 'push')
            **kwargs: Additional command arguments

        Returns:
            ToolResult with command output
        """
        try:
            # Build git command
            cmd = ['git', command]
            if kwargs:
                for key, value in kwargs.items():
                    cmd.extend([f'--{key}', str(value)])

            logger.info(f"Executing git command: {' '.join(cmd)}")

            # Placeholder: Execute actual git command
            # result = subprocess.run(cmd, capture_output=True, text=True, cwd=repo_path)

            output = {
                'command': command,
                'status': 'success',
                'output': f"Git {command} placeholder - implement actual execution"
            }

            return ToolResult(
                success=True,
                output=output,
                metadata={'command': command}
            )

        except Exception as e:
            logger.error(f"Git command failed: {e}")
            return ToolResult(
                success=False,
                output=None,
                error=str(e)
            )

    def status(self, repo_path: Optional[str] = None) -> ToolResult:
        """Get git status."""
        return self.execute('status', porcelain=True)

    def add(self, files: List[str]) -> ToolResult:
        """Stage files for commit."""
        return self.execute('add', *files)

    def commit(self, message: str) -> ToolResult:
        """Commit staged changes."""
        full_message = f"{self.commit_prefix} {message}"
        return self.execute('commit', message=full_message)

    def push(self, remote: str = 'origin', branch: Optional[str] = None) -> ToolResult:
        """Push to remote."""
        cmd = 'push'
        params = {'remote': remote}
        if branch:
            params['branch'] = branch
        return self.execute(cmd, **params)

    def pull(self, remote: str = 'origin', branch: Optional[str] = None) -> ToolResult:
        """Pull from remote."""
        cmd = 'pull'
        params = {'remote': remote}
        if branch:
            params['branch'] = branch
        return self.execute(cmd, **params)

    def branch(self, list_branches: bool = True) -> ToolResult:
        """List branches."""
        return self.execute('branch', all=list_branches)

    def log(self, max_count: int = 10) -> ToolResult:
        """Get commit history."""
        return self.execute('log', max_count=max_count)

    def get_schema(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'parameters': {
                'type': 'object',
                'properties': {
                    'command': {
                        'type': 'string',
                        'description': 'Git subcommand',
                        'enum': ['status', 'add', 'commit', 'push', 'pull', 'branch', 'log']
                    }
                },
                'required': ['command']
            }
        }
