# .claudebot/agents/spec_agent.py
"""Spec generation agent"""

import os
import logging
from typing import Optional

from .base_agent import BaseAgent, AgentContext, AgentResult
from ..tools.claude_cli import ClaudeCLI

logger = logging.getLogger(__name__)

class SpecAgent(BaseAgent):
    """Agent for generating specifications"""

    name = "spec"
    description = "Generate specification documents"

    SYSTEM_PROMPT = """You are an expert technical writer. Create clear, detailed specifications.

Format: Markdown
Sections:
1. Overview
2. Requirements
3. Technical Design
4. API Specification (if applicable)
5. Acceptance Criteria"""

    async def execute(self, task: dict, context: AgentContext) -> AgentResult:
        """Execute spec generation"""
        is_valid, error = self.validate_input(task)
        if not is_valid:
            return AgentResult(success=False, summary=error, error=error)

        description = task.get("description", "")

        # Check for existing SPEC.md
        spec_path = os.path.join(context.repo_path, "SPEC.md")
        existing_spec = ""
        if os.path.exists(spec_path):
            with open(spec_path, 'r') as f:
                existing_spec = f.read()

        prompt = f"Generate specification for: {description}\n\n"
        if existing_spec:
            prompt += f"Existing spec:\n{existing_spec}\n"

        claude = ClaudeCLI(context.claude_api_key)
        try:
            result = await claude.complete(prompt, self.SYSTEM_PROMPT)

            # Write SPEC.md
            with open(spec_path, 'w') as f:
                f.write(result)

            return AgentResult(
                success=True,
                summary="Generated SPEC.md",
                files_created=["SPEC.md"]
            )

        except Exception as e:
            logger.exception("Spec generation failed")
            return await self.on_error(e, task)

    def validate_input(self, task: dict) -> tuple[bool, Optional[str]]:
        """Validate task input"""
        if not task.get("description"):
            return False, "Description is required"
        return True, None
