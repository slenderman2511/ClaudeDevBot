# .claudebot/tools/claude_cli.py
"""Claude CLI wrapper"""

import subprocess
import json
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class ClaudeCLI:
    """Wrapper for Claude Code CLI"""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key
        self.model = model
        self.env = os.environ.copy()
        self.env["ANTHROPIC_API_KEY"] = api_key

    async def complete(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Send a prompt to Claude and get completion"""
        cmd = ["claude", "--print", prompt]

        if system_prompt:
            cmd.insert(2, "--system")
            cmd.insert(3, system_prompt)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=self.env,
                timeout=300
            )

            if result.returncode != 0:
                raise RuntimeError(f"Claude CLI error: {result.stderr}")

            return result.stdout

        except subprocess.TimeoutExpired:
            raise TimeoutError("Claude CLI timed out")
        except FileNotFoundError:
            raise RuntimeError("Claude CLI not found. Please install Claude Code.")

    async def complete_json(self, prompt: str, system_prompt: Optional[str] = None) -> dict:
        """Send a prompt to Claude and parse JSON response"""
        full_prompt = f"{prompt}\n\nRespond with valid JSON only."
        result = await self.complete(full_prompt, system_prompt)
        try:
            return json.loads(result)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}")
