"""
Code Agent Module

Specialized agent for generating implementation code using Claude CLI.
"""

import logging
import time
from typing import Dict, Any, Optional
from agents.base_agent import BaseAgent, Task, AgentResult
from tools.claude_cli import ClaudeCLITool

logger = logging.getLogger(__name__)


class CodeAgent(BaseAgent):
    """
    Agent responsible for generating implementation code.

    Uses Claude CLI to generate code implementations from requirements.
    """

    def __init__(self, config: Dict[str, Any] = None, claude_tool: Optional[ClaudeCLITool] = None):
        super().__init__(
            name="code_agent",
            model=config.get('model', 'sonnet') if config else 'sonnet',
            max_iterations=config.get('max_iterations', 20) if config else 20,
            timeout=config.get('timeout', 600) if config else 600,
            config=config or {}
        )
        # Use provided tool or create new one
        self._claude = claude_tool or ClaudeCLITool(config.get('claude', {}))

    def execute(self, task: Task) -> AgentResult:
        """
        Execute code generation task.

        Args:
            task: Task containing specification/requirement

        Returns:
            AgentResult with code output
        """
        start_time = time.time()

        if not self.validate_input(task.input):
            return AgentResult(
                success=False,
                output="",
                error="Invalid input: specification cannot be empty"
            )

        logger.info(f"Generating code for: {task.input[:100]}...")

        try:
            # Build prompt for code generation
            prompt = self._build_code_prompt(task.input)

            # Execute via Claude CLI
            result = self._claude.execute(prompt, task_type='code', model=self.model)

            if result.success:
                execution_time = time.time() - start_time
                return AgentResult(
                    success=True,
                    output=result.output.get('response', str(result.output)),
                    artifacts={'language': 'python', 'model': self.model},
                    execution_time=execution_time,
                    iterations=1
                )
            else:
                return AgentResult(
                    success=False,
                    output="",
                    error=result.error or "Code generation failed"
                )

        except Exception as e:
            logger.exception("Code agent execution failed")
            return AgentResult(
                success=False,
                output="",
                error=f"Code agent error: {str(e)}"
            )

    def _build_code_prompt(self, requirement: str) -> str:
        """Build a detailed prompt for code generation."""
        return f"""Generate implementation code for the following requirement:

{requirement}

Provide:
1. Clean, well-documented code
2. Proper error handling
3. Type hints where appropriate
4. Usage examples if applicable

If this is a feature implementation, provide the complete code with all necessary components."""

    def get_capabilities(self) -> list:
        return [
            "generate_python",
            "generate_javascript",
            "generate_typescript",
            "generate_rest_api",
            "generate_cli"
        ]
