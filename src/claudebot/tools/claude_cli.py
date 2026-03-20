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
        """Send a prompt to Claude and get completion as plain text."""
        cmd = ["claude", "--print", "--output-format", "json"]

        if system_prompt:
            cmd.extend(["--system", system_prompt])

        cmd.append(prompt)

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self.env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=300
                )
            except asyncio.TimeoutError:
                process.kill()
                raise TimeoutError("Claude CLI timed out")

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise RuntimeError(f"Claude CLI error: {error_msg}")

            # Parse JSON response from --output-format json
            import json
            try:
                data = json.loads(stdout.decode())
                return data.get("content", stdout.decode())
            except json.JSONDecodeError:
                # Fallback: return raw output if not valid JSON
                return stdout.decode()

        except FileNotFoundError:
            raise RuntimeError("Claude CLI not found. Please install Claude Code.")

    async def complete_json(self, prompt: str, system_prompt: Optional[str] = None) -> dict:
        """Send a prompt to Claude and parse structured JSON response."""
        cmd = ["claude", "--print", "--output-format", "json"]

        if system_prompt:
            cmd.extend(["--system", system_prompt])

        cmd.append(prompt)

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self.env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=300
                )
            except asyncio.TimeoutError:
                process.kill()
                raise TimeoutError("Claude CLI timed out")

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                raise RuntimeError(f"Claude CLI error: {error_msg}")

            import json
            return json.loads(stdout.decode())

        except FileNotFoundError:
            raise RuntimeError("Claude CLI not found. Please install Claude Code.")
