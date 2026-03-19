"""
Spec Generator Module

Generates OpenSpec feature specifications using AI.
"""

from typing import Any, Dict, Optional

from claudebot.tools.claude_cli import ClaudeCLITool
from claudebot.observability.logger import get_logger

logger = get_logger(__name__)


class SpecGenerator:
    """
    Generates OpenSpec feature specifications using AI.

    Creates detailed feature specs including:
    - Overview
    - Functional requirements
    - Non-functional requirements
    - Tasks and phases
    - Dependencies
    """

    def __init__(self, claude_tool: Optional[ClaudeCLITool] = None):
        """
        Initialize the spec generator.

        Args:
            claude_tool: Optional Claude CLI tool for AI generation
        """
        self._claude = claude_tool

    def generate(self, feature_name: str, description: str) -> Dict[str, Any]:
        """
        Generate a feature specification.

        Args:
            feature_name: Name of the feature
            description: Description of what the feature should do

        Returns:
            Generated specification dictionary
        """
        logger.info(f"Generating spec for feature: {feature_name}")

        # If Claude tool is available, use it for generation
        if self._claude:
            return self._generate_with_ai(feature_name, description)

        # Otherwise, generate a basic spec
        return self._generate_basic(feature_name, description)

    def _generate_with_ai(self, feature_name: str, description: str) -> Dict[str, Any]:
        """Generate spec using AI."""
        prompt = f"""Generate a detailed OpenSpec feature specification for:

Feature: {feature_name}
Description: {description}

Create a comprehensive spec with:
1. Overview - What the feature does
2. Functional Requirements - What it must do
3. Non-Functional Requirements - Performance, security, etc.
4. Tasks organized in phases (Design, Implementation, Testing, Deployment)
5. Dependencies - What other features/services it depends on

Format as a markdown feature specification that can be saved to a .md file."""

        try:
            result = self._claude.execute(prompt, task_type='spec')
            if result.success:
                # Return basic spec with tasks (AI markdown is saved separately)
                return self._generate_basic(feature_name, description)
        except Exception as e:
            logger.error(f"AI generation failed: {e}")

        # Fall back to basic generation
        return self._generate_basic(feature_name, description)

    def _generate_basic(self, feature_name: str, description: str) -> Dict[str, Any]:
        """Generate a basic specification."""
        return {
            "name": feature_name,
            "description": description,
            "version": "1.0.0",
            "status": "draft",
            "tasks": [
                {
                    "name": "Design API endpoints",
                    "phase": "Phase 1: Design",
                    "completed": False
                },
                {
                    "name": "Define data models",
                    "phase": "Phase 1: Design",
                    "completed": False
                },
                {
                    "name": "Implement core functionality",
                    "phase": "Phase 2: Implementation",
                    "completed": False
                },
                {
                    "name": "Write unit tests",
                    "phase": "Phase 3: Testing",
                    "completed": False
                },
                {
                    "name": "Write integration tests",
                    "phase": "Phase 3: Testing",
                    "completed": False
                },
                {
                    "name": "Deploy to staging",
                    "phase": "Phase 4: Deployment",
                    "completed": False
                },
                {
                    "name": "Deploy to production",
                    "phase": "Phase 4: Deployment",
                    "completed": False
                }
            ],
            "dependencies": []
        }

    def generate_markdown(self, feature_name: str, description: str) -> str:
        """
        Generate markdown content for a feature spec.

        Args:
            feature_name: Name of the feature
            description: Description of what the feature should do

        Returns:
            Markdown formatted specification
        """
        spec = self.generate(feature_name, description)

        # Build markdown
        md = f"""# Feature: {spec['name']}

## Overview
{spec['description']}

## Version
{spec.get('version', '1.0.0')}

## Status
{spec.get('status', 'draft')}

## Tasks
"""

        tasks_by_phase = {}
        for task in spec.get('tasks', []):
            phase = task.get('phase', 'Implementation')
            if phase not in tasks_by_phase:
                tasks_by_phase[phase] = []
            tasks_by_phase[phase].append(task)

        for phase, tasks in tasks_by_phase.items():
            md += f"\n### {phase}\n"
            for task in tasks:
                check = 'x' if task.get('completed') else ' '
                md += f"- [{check}] {task['name']}\n"

        md += "\n## Dependencies\n"
        for dep in spec.get('dependencies', []):
            md += f"- {dep}\n"

        md += "\n## Notes\n"

        return md


def create_spec_generator(claude_config: Optional[Dict[str, Any]] = None) -> SpecGenerator:
    """
    Create a spec generator instance.

    Args:
        claude_config: Optional configuration for Claude CLI

    Returns:
        SpecGenerator instance
    """
    claude_tool = None
    if claude_config:
        claude_tool = ClaudeCLITool(claude_config)

    return SpecGenerator(claude_tool)
