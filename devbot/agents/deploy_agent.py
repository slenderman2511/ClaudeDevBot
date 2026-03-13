"""
Deploy Agent Module

Specialized agent for handling deployment workflows using Claude CLI.
"""

import subprocess
import time
from typing import Dict, Any, Optional

from devbot.agents.base_agent import BaseAgent, Task, AgentResult
from devbot.tools.claude_cli import ClaudeCLITool
from devbot.observability.logger import get_logger

logger = get_logger(__name__)


class DeployAgent(BaseAgent):
    """
    Agent responsible for handling deployment workflows.

    Uses Claude CLI to assist with deployment planning and execution.
    """

    def __init__(self, config: Dict[str, Any] = None, claude_tool: Optional[ClaudeCLITool] = None):
        super().__init__(
            name="deploy_agent",
            model=config.get('model', 'sonnet') if config else 'sonnet',
            max_iterations=config.get('max_iterations', 5) if config else 5,
            timeout=config.get('timeout', 600) if config else 600,
            config=config or {}
        )
        self._claude = claude_tool or ClaudeCLITool(config.get('claude', {}))

    def execute(self, task: Task) -> AgentResult:
        """Execute deployment task."""
        start_time = time.time()

        if not self.validate_input(task.input):
            return AgentResult(
                success=False,
                output="",
                error="Invalid input: deployment target cannot be empty"
            )

        logger.info(f"Deploying to: {task.input[:100]}...")

        try:
            deployment_result = self._detect_and_execute_deployment(task.input)

            if deployment_result['executed']:
                execution_time = time.time() - start_time
                return AgentResult(
                    success=True,
                    output=deployment_result['output'],
                    artifacts={'target': task.input, 'status': 'deployed'},
                    execution_time=execution_time,
                    iterations=1
                )

            # Fall back to Claude CLI for deployment assistance
            prompt = self._build_deploy_prompt(task.input)
            result = self._claude.execute(prompt, task_type='deploy', model=self.model)

            if result.success:
                execution_time = time.time() - start_time
                return AgentResult(
                    success=True,
                    output=result.output.get('response', str(result.output)),
                    artifacts={'target': task.input, 'status': 'planned'},
                    execution_time=execution_time,
                    iterations=1
                )
            else:
                return AgentResult(
                    success=False,
                    output="",
                    error=result.error or "Deployment failed"
                )

        except Exception as e:
            logger.exception("Deploy agent execution failed")
            return AgentResult(
                success=False,
                output="",
                error=f"Deploy agent error: {str(e)}"
            )

    def _detect_and_execute_deployment(self, target: str) -> Dict[str, Any]:
        """Detect deployment type and execute if possible."""
        target_lower = target.lower()

        if 'vercel' in target_lower:
            return self._deploy_vercel()
        elif 'docker' in target_lower:
            return self._deploy_docker()
        elif 'heroku' in target_lower:
            return self._deploy_heroku()

        return {'executed': False, 'output': ''}

    def _deploy_vercel(self) -> Dict[str, Any]:
        """Deploy using Vercel CLI."""
        try:
            result = subprocess.run(
                ['vercel', '--yes'],
                capture_output=True,
                text=True,
                timeout=300
            )
            return {
                'executed': True,
                'output': f"Vercel deployment:\n{result.stdout}\n{result.stderr}"
            }
        except FileNotFoundError:
            return {'executed': False, 'output': 'Vercel CLI not installed'}
        except Exception as e:
            return {'executed': True, 'output': f"Vercel deployment failed: {e}"}

    def _deploy_docker(self) -> Dict[str, Any]:
        """Deploy using Docker."""
        try:
            result = subprocess.run(
                ['docker', 'build', '-t', 'app:latest', '.'],
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode == 0:
                return {
                    'executed': True,
                    'output': f"Docker build successful. Run 'docker run app:latest' to start."
                }
            else:
                return {'executed': True, 'output': f"Docker build failed: {result.stderr}"}
        except FileNotFoundError:
            return {'executed': False, 'output': 'Docker not installed'}
        except Exception as e:
            return {'executed': True, 'output': f"Docker deployment failed: {e}"}

    def _deploy_heroku(self) -> Dict[str, Any]:
        """Deploy using Heroku CLI."""
        try:
            result = subprocess.run(
                ['git', 'push', 'heroku', 'main'],
                capture_output=True,
                text=True,
                timeout=300
            )
            return {
                'executed': True,
                'output': f"Heroku deployment:\n{result.stdout}\n{result.stderr}"
            }
        except Exception as e:
            return {'executed': True, 'output': f"Heroku deployment failed: {e}"}

    def _build_deploy_prompt(self, target: str) -> str:
        """Build prompt for deployment assistance."""
        return f"""Help with deploying to the following target:

{target}

Provide:
1. Deployment Steps - Step-by-step instructions
2. Prerequisites - What needs to be set up
3. Configuration - Required environment variables
4. Verification - How to verify deployment"""

    def get_capabilities(self) -> list:
        return [
            "deploy_to_vercel",
            "deploy_to_aws",
            "deploy_to_docker",
            "deploy_to_kubernetes"
        ]
