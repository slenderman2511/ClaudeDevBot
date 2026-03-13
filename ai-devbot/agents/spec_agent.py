"""
Spec Agent Module

Specialized agent for generating specification documents using Claude CLI.
"""

import logging
import time
from typing import Dict, Any, Optional
from agents.base_agent import BaseAgent, Task, AgentResult
from tools.claude_cli import ClaudeCLITool

logger = logging.getLogger(__name__)


class SpecAgent(BaseAgent):
    """
    Agent responsible for generating specification documents.

    Uses Claude CLI to generate detailed specification documents from requirements.
    """

    def __init__(self, config: Dict[str, Any] = None, claude_tool: Optional[ClaudeCLITool] = None, openspec=None):
        super().__init__(
            name="spec_agent",
            model=config.get('model', 'sonnet') if config else 'sonnet',
            max_iterations=config.get('max_iterations', 10) if config else 10,
            timeout=config.get('timeout', 300) if config else 300,
            config=config or {}
        )
        # Use provided tool or create new one
        self._claude = claude_tool or ClaudeCLITool(config.get('claude', {}))
        # OpenSpec for saving specs
        self._openspec = openspec

    def execute(self, task: Task) -> AgentResult:
        """
        Execute specification generation task.

        Args:
            task: Task containing requirements

        Returns:
            AgentResult with specification output
        """
        start_time = time.time()

        if not self.validate_input(task.input):
            return AgentResult(
                success=False,
                output="",
                error="Invalid input: requirements cannot be empty"
            )

        self.log(logging.INFO, f"Generating specification for: {task.input[:100]}...")

        try:
            # Build prompt for specification
            prompt = self._build_spec_prompt(task.input)

            # Execute via Claude CLI
            result = self._claude.execute(prompt, task_type='spec', model=self.model)

            if result.success:
                execution_time = time.time() - start_time

                # Save to OpenSpec if available
                spec_saved = False
                if self._openspec:
                    feature_name = self._extract_feature_name(task.input)
                    if feature_name:
                        try:
                            self._openspec.create_feature(feature_name, result.output.get('response', ''))
                            spec_saved = True
                            logger.info(f"Saved spec to OpenSpec: {feature_name}")
                        except Exception as e:
                            logger.warning(f"Failed to save spec to OpenSpec: {e}")

                return AgentResult(
                    success=True,
                    output=result.output.get('response', str(result.output)),
                    artifacts={'spec_type': 'product_specification', 'model': self.model, 'spec_saved': spec_saved},
                    execution_time=execution_time,
                    iterations=1
                )
            else:
                return AgentResult(
                    success=False,
                    output="",
                    error=result.error or "Specification generation failed"
                )

        except Exception as e:
            logger.exception("Spec agent execution failed")
            return AgentResult(
                success=False,
                output="",
                error=f"Spec agent error: {str(e)}"
            )

    def _build_spec_prompt(self, requirements: str) -> str:
        """Build a detailed prompt for specification generation."""
        return f"""Generate a detailed specification document for the following requirement:

{requirements}

Include these sections:
1. **Overview** - Brief description of what this feature does
2. **Functional Requirements** - List of specific functional requirements
3. **Non-Functional Requirements** - Performance, security, scalability considerations
4. **User Stories** - 3-5 user stories in Gherkin format (As a..., I want..., So that...)
5. **Technical Considerations** - Architecture, dependencies, API design
6. **Acceptance Criteria** - Clear, testable criteria for success

Provide a comprehensive but concise specification that a developer could use to implement this feature."""

    def get_capabilities(self) -> list:
        return [
            "generate_product_spec",
            "generate_technical_spec",
            "generate_api_spec",
            "generate_architecture_spec"
        ]

    def _extract_feature_name(self, requirement: str) -> Optional[str]:
        """Extract feature name from requirement."""
        import re
        match = re.search(r'([a-zA-Z][a-zA-Z0-9-]+)', requirement)
        if match:
            return match.group(1).lower()
        return None
