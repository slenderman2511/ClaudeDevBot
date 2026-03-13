"""
Claude CLI Tool

Wrapper for Claude Code CLI operations.
"""

import subprocess
import json
import logging
from typing import Any, Dict, Optional
from tools.tool import Tool, ToolResult

logger = logging.getLogger(__name__)


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

    def execute(self, prompt: str, **kwargs) -> ToolResult:
        """
        Execute a Claude CLI command.

        Args:
            prompt: The prompt to send to Claude
            **kwargs: Additional parameters

        Returns:
            ToolResult with Claude's response
        """
        try:
            # Placeholder: Build actual Claude CLI command
            # cmd = [self.cli_path, 'generate', '--prompt', prompt, '--model', self.model]
            logger.info(f"Executing Claude CLI with prompt: {prompt[:100]}...")

            # Placeholder response
            output = {
                'status': 'success',
                'response': f"Claude CLI response for: {prompt[:50]}...",
                'model': self.model
            }

            return ToolResult(
                success=True,
                output=output,
                metadata={'cli_path': self.cli_path}
            )

        except Exception as e:
            logger.error(f"Claude CLI execution failed: {e}")
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
                        'description': 'The prompt to send to Claude'
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
