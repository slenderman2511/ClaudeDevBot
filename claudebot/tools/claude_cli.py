# .claudebot/tools/claude_cli.py
"""Claude CLI wrapper"""

import asyncio
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
        cmd = ["claude", "--print", "--no-color"]

        if system_prompt:
            cmd.extend(["--system", system_prompt])

        # Add prompt as last argument
        cmd.append(prompt)

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self.env
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=300
                )
            except asyncio.TimeoutError:
                process.kill()
                raise TimeoutError("Claude CLI timed out")

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise RuntimeError(f"Claude CLI error: {error_msg}")

            return stdout.decode()

        except FileNotFoundError:
            raise RuntimeError("Claude CLI not found. Please install Claude Code.")

    async def complete_json(self, prompt: str, system_prompt: Optional[str] = None) -> dict:
        """Send a prompt to Claude and parse JSON response"""
        full_prompt = f"{prompt}\n\nRespond with valid JSON only."
        result = await self.complete(full_prompt, system_prompt)
        import json
        try:
            return json.loads(result)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}")
