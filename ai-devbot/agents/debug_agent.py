"""
Debug Agent Module

Specialized agent for analyzing and fixing issues using Claude CLI.
"""

import logging
import time
from typing import Dict, Any, Optional
from agents.base_agent import BaseAgent, Task, AgentResult
from tools.claude_cli import ClaudeCLITool

logger = logging.getLogger(__name__)


class DebugAgent(BaseAgent):
    """
    Agent responsible for analyzing and fixing issues.

    Uses Claude CLI to analyze errors and provide debugging assistance.
    """

    def __init__(self, config: Dict[str, Any] = None, claude_tool: Optional[ClaudeCLITool] = None):
        super().__init__(
            name="debug_agent",
            model=config.get('model', 'sonnet') if config else 'sonnet',
            max_iterations=config.get('max_iterations', 10) if config else 10,
            timeout=config.get('timeout', 300) if config else 300,
            config=config or {}
        )
        # Use provided tool or create new one
        self._claude = claude_tool or ClaudeCLITool(config.get('claude', {}))

    def execute(self, task: Task) -> AgentResult:
        """
        Execute debugging task.

        Args:
            task: Task containing error description

        Returns:
            AgentResult with debugging analysis
        """
        start_time = time.time()

        if not self.validate_input(task.input):
            return AgentResult(
                success=False,
                output="",
                error="Invalid input: error description cannot be empty"
            )

        logger.info(f"Analyzing issue: {task.input[:100]}...")

        try:
            # Build prompt for debugging
            prompt = self._build_debug_prompt(task.input)

            # Execute via Claude CLI
            result = self._claude.execute(prompt, task_type='debug', model=self.model)

            if result.success:
                execution_time = time.time() - start_time
                return AgentResult(
                    success=True,
                    output=result.output.get('response', str(result.output)),
                    artifacts={'issue_type': 'general', 'model': self.model},
                    execution_time=execution_time,
                    iterations=1
                )
            else:
                return AgentResult(
                    success=False,
                    output="",
                    error=result.error or "Debug analysis failed"
                )

        except Exception as e:
            logger.exception("Debug agent execution failed")
            return AgentResult(
                success=False,
                output="",
                error=f"Debug agent error: {str(e)}"
            )

    def _build_debug_prompt(self, issue: str) -> str:
        """Build prompt for debugging assistance."""
        return f"""Analyze and help debug the following issue:

{issue}

Provide a detailed analysis including:
1. **Possible Causes** - What could be causing this issue
2. **Debugging Steps** - How to investigate the problem
3. **Suggested Fixes** - Potential solutions to try
4. **Prevention** - How to avoid this issue in the future

If this is a code error, look for common patterns that cause this type of issue."""

    def get_capabilities(self) -> list:
        return [
            "analyze_error",
            "suggest_fix",
            "analyze_stack_trace",
            "analyze_performance"
        ]
