"""
Code Agent Module

Specialized agent for generating implementation code using Claude CLI.
"""

import time
import re
from typing import Dict, Any, Optional

from devbot.agents.base_agent import BaseAgent, Task, AgentResult
from devbot.tools.claude_cli import ClaudeCLITool
from devbot.observability.logger import get_logger

logger = get_logger(__name__)


class CodeAgent(BaseAgent):
    """
    Agent responsible for generating implementation code.

    Uses Claude CLI to generate code implementations from requirements.
    """

    def __init__(self, config: Dict[str, Any] = None, claude_tool: Optional[ClaudeCLITool] = None, openspec=None):
        super().__init__(
            name="code_agent",
            model=config.get('model', 'sonnet') if config else 'sonnet',
            max_iterations=config.get('max_iterations', 20) if config else 20,
            timeout=config.get('timeout', 600) if config else 600,
            config=config or {}
        )
        self._claude = claude_tool or ClaudeCLITool(config.get('claude', {}))
        self._openspec = openspec

    def execute(self, task: Task) -> AgentResult:
        """Execute code generation task."""
        start_time = time.time()

        if not self.validate_input(task.input):
            return AgentResult(
                success=False,
                output="",
                error="Invalid input: specification cannot be empty"
            )

        logger.info(f"Generating code for: {task.input[:100]}...")

        # Load OpenSpec context if available
        spec_context = ""
        if self._openspec:
            feature_name = self._extract_feature_name(task.input)
            if feature_name:
                spec = self._openspec.load_feature(feature_name)
                if spec:
                    spec_context = self._format_spec_context(spec)
                    logger.info(f"Loaded OpenSpec context for: {feature_name}")

        try:
            # Build prompt for code generation
            prompt = self._build_code_prompt(task.input, spec_context)

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

    def _extract_feature_name(self, requirement: str) -> Optional[str]:
        """Extract feature name from requirement."""
        match = re.search(r'(?:implement|for|feature[:\s]+)(\w+(?:-\w+)*)', requirement, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _format_spec_context(self, spec: Dict[str, Any]) -> str:
        """Format OpenSpec context for prompt."""
        context = f"\n\n## OpenSpec Context\n"
        context += f"Feature: {spec.get('name')}\n"
        context += f"Version: {spec.get('version')}\n"
        context += f"Status: {spec.get('status')}\n\n"

        pending = [t for t in spec.get('tasks', []) if not t.get('completed')]
        if pending:
            context += "Current tasks to implement:\n"
            for task in pending[:5]:
                context += f"- [{task['phase']}] {task['name']}\n"

        deps = spec.get('dependencies', [])
        if deps:
            context += f"\nDependencies: {', '.join(deps)}\n"

        return context

    def _build_code_prompt(self, requirement: str, spec_context: str = "") -> str:
        """Build a detailed prompt for code generation."""
        return f"""Generate implementation code for the following requirement:

{requirement}
{spec_context}

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
