"""
Claude CLI Tool

Wrapper for Claude Code CLI operations.
"""

import subprocess
import json
import os
from typing import Any, Dict, Optional

from devbot.tools.tool import Tool, ToolResult
from devbot.observability.logger import get_logger

logger = get_logger(__name__)


class ClaudeCLITool(Tool):
    """
    Tool for interacting with Claude Code CLI.

    Provides capabilities for running Claude commands and parsing responses.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            name="claude_cli",
            description="Execute Claude Code CLI commands for AI-powered code generation and analysis",
            config=config or {}
        )
        self.cli_path = self.config.get('cli_path', 'claude')
        self.model = self.config.get('model', 'sonnet')
        self.max_tokens = self.config.get('max_tokens', 4096)
        self.temperature = self.config.get('temperature', 0.7)
        self.project_context = self.config.get('project_context', '.')

    def execute(self, prompt: str, **kwargs) -> ToolResult:
        """
        Execute a Claude CLI command.

        Args:
            prompt: The prompt/requirement to send to Claude
            **kwargs: Additional parameters (task_type, model, etc.)

        Returns:
            ToolResult with Claude's response
        """
        task_type = kwargs.get('task_type', 'general')
        model = kwargs.get('model', self.model)

        try:
            # Build Claude CLI command
            cmd = [
                self.cli_path,
                '-p',  # Print mode (non-interactive)
                '--dangerously-skip-permissions',  # Skip permission prompts
                '--model', model,
                prompt
            ]

            logger.info(f"Executing Claude CLI with prompt: {prompt[:80]}...")

            # Create clean environment
            env = os.environ.copy()
            env.pop('CLAUDECODE', None)

            # Execute command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.project_context,
                env=env
            )

            if result.returncode == 0:
                output = {
                    'status': 'success',
                    'response': result.stdout,
                    'model': model,
                    'task_type': task_type
                }
                return ToolResult(
                    success=True,
                    output=output,
                    metadata={'cli_path': self.cli_path, 'return_code': result.returncode}
                )
            else:
                error_msg = result.stderr or "Unknown error"
                logger.error(f"Claude CLI error: {error_msg}")
                return ToolResult(
                    success=False,
                    output=None,
                    error=error_msg
                )

        except subprocess.TimeoutExpired:
            logger.error("Claude CLI timeout")
            return ToolResult(
                success=False,
                output=None,
                error="Claude CLI command timed out"
            )
        except FileNotFoundError:
            logger.error("Claude CLI not found")
            return ToolResult(
                success=False,
                output=None,
                error="Claude CLI not found. Please install: npm install -g @anthropic-ai/claude-code"
            )
        except Exception as e:
            logger.error(f"Claude CLI execution failed: {e}")
            return ToolResult(
                success=False,
                output=None,
                error=str(e)
            )

    def execute_with_session(self, session_id: str, message: str, **kwargs) -> ToolResult:
        """
        Send a message to an existing Claude session.

        Args:
            session_id: Session ID to continue
            message: Message to send
            **kwargs: Additional parameters

        Returns:
            ToolResult with Claude's response
        """
        try:
            cmd = [
                self.cli_path,
                'session',
                'send',
                session_id,
                message
            ]

            logger.info(f"Sending to Claude session {session_id}: {message[:50]}...")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.project_context
            )

            if result.returncode == 0:
                return ToolResult(
                    success=True,
                    output={'response': result.stdout},
                    metadata={'session_id': session_id}
                )
            else:
                return ToolResult(
                    success=False,
                    output=None,
                    error=result.stderr
                )

        except Exception as e:
            logger.error(f"Claude session send failed: {e}")
            return ToolResult(
                success=False,
                output=None,
                error=str(e)
            )

    def validate(self) -> bool:
        """Check if Claude CLI is available."""
        try:
            result = subprocess.run(
                [self.cli_path, '--version'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def get_schema(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'description': self.description,
            'parameters': {
                'type': 'object',
                'properties': {
                    'prompt': {
                        'type': 'string',
                        'description': 'The prompt/requirement to send to Claude'
                    },
                    'task_type': {
                        'type': 'string',
                        'description': 'Type of task (spec, code, test, debug)',
                        'enum': ['spec', 'code', 'test', 'debug', 'general']
                    },
                    'model': {
                        'type': 'string',
                        'description': 'Model to use',
                        'enum': ['haiku', 'sonnet', 'opus']
                    }
                },
                'required': ['prompt']
            }
        }


def create_claude_tool(config: Optional[Dict[str, Any]] = None) -> ClaudeCLITool:
    """Factory function to create Claude CLI tool."""
    return ClaudeCLITool(config)
