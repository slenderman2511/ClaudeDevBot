"""
Test Agent Module

Specialized agent for running and generating tests using Claude CLI.
"""

import logging
import time
import subprocess
from typing import Dict, Any, Optional
from agents.base_agent import BaseAgent, Task, AgentResult
from tools.claude_cli import ClaudeCLITool

logger = logging.getLogger(__name__)


class TestAgent(BaseAgent):
    """
    Agent responsible for running and generating tests.

    Uses Claude CLI to help with test execution and generation.
    """

    def __init__(self, config: Dict[str, Any] = None, claude_tool: Optional[ClaudeCLITool] = None):
        super().__init__(
            name="test_agent",
            model=config.get('model', 'haiku') if config else 'haiku',
            max_iterations=config.get('max_iterations', 15) if config else 15,
            timeout=config.get('timeout', 300) if config else 300,
            config=config or {}
        )
        # Use provided tool or create new one
        self._claude = claude_tool or ClaudeCLITool(config.get('claude', {}))

    def execute(self, task: Task) -> AgentResult:
        """
        Execute test task.

        Args:
            task: Task containing test scope

        Returns:
            AgentResult with test results
        """
        start_time = time.time()

        if not self.validate_input(task.input):
            return AgentResult(
                success=False,
                output="",
                error="Invalid input: test scope cannot be empty"
            )

        logger.info(f"Running tests for: {task.input[:100]}...")

        try:
            # First, try to run actual tests using pytest
            test_result = self._run_pytest(task.input)

            if test_result['ran']:
                # Tests ran successfully - use those results
                output = test_result['output']
                execution_time = time.time() - start_time

                return AgentResult(
                    success=True,
                    output=output,
                    artifacts={
                        'tests_passed': test_result.get('passed', 0),
                        'tests_failed': test_result.get('failed', 0),
                        'tests_skipped': test_result.get('skipped', 0)
                    },
                    execution_time=execution_time,
                    iterations=1
                )
            else:
                # No tests ran - use Claude to help
                prompt = self._build_test_prompt(task.input)
                result = self._claude.execute(prompt, task_type='test', model=self.model)

                if result.success:
                    execution_time = time.time() - start_time
                    return AgentResult(
                        success=True,
                        output=result.output.get('response', str(result.output)),
                        artifacts={'tests_passed': 0, 'tests_failed': 0, 'tests_skipped': 0},
                        execution_time=execution_time,
                        iterations=1
                    )
                else:
                    return AgentResult(
                        success=False,
                        output="",
                        error=result.error or "Test execution failed"
                    )

        except Exception as e:
            logger.exception("Test agent execution failed")
            return AgentResult(
                success=False,
                output="",
                error=f"Test agent error: {str(e)}"
            )

    def _run_pytest(self, scope: str) -> Dict[str, Any]:
        """Try to run pytest for the given scope."""
        try:
            # Determine scope for pytest
            if scope.lower() in ['all', '']:
                cmd = ['pytest', '-v', '--tb=short']
            else:
                # Try to match scope to test files/paths
                cmd = ['pytest', '-v', '--tb=short', '-k', scope]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            return {
                'ran': True,
                'output': result.stdout + result.stderr,
                'passed': result.stdout.count(' PASSED'),
                'failed': result.stdout.count(' FAILED'),
                'skipped': result.stdout.count(' SKIPPED'),
                'returncode': result.returncode
            }
        except FileNotFoundError:
            # pytest not installed
            return {'ran': False}
        except Exception as e:
            logger.warning(f"Pytest execution failed: {e}")
            return {'ran': False}

    def _build_test_prompt(self, scope: str) -> str:
        """Build prompt for test assistance."""
        return f"""Help with testing for the following scope:

{scope}

Provide:
1. Suggestions for what tests should be written
2. Test cases that would ensure proper coverage
3. Any existing issues you notice in the code that tests should catch

If there's a specific error or issue, analyze it and suggest test cases that would help identify the problem."""

    def get_capabilities(self) -> list:
        return [
            "run_pytest",
            "run_unittest",
            "generate_tests",
            "run_integration_tests"
        ]
