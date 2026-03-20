# .claudebot/agents/test_agent.py
"""Test generation agent"""

import os
import re
import logging
from typing import Optional, List

from .base_agent import BaseAgent, AgentContext, AgentResult
from ..tools.claude_cli import ClaudeCLI

logger = logging.getLogger(__name__)


class TestAgent(BaseAgent):
    """Agent for generating unit tests"""

    name = "test"
    description = "Generate unit tests from code"

    SYSTEM_PROMPT = """You are an expert software developer specializing in testing.
Generate comprehensive unit tests for the provided code.

Requirements:
1. Use pytest for Python or jest/vitest for JavaScript/TypeScript
2. Follow testing best practices ( Arrange-Act-Assert pattern)
3. Test edge cases and error conditions
4. Use mocking where appropriate
5. Include both positive and negative test cases

Output format:
- For multiple files, separate with ---FILE:filepath---
- Include only the test file content, no explanations"""

    TEST_FRAMEWORKS = {
        "python": {
            "extension": ".py",
            "pattern": r"^(test_.*\.py|.*_test\.py)$",
            "default": "test_{module}.py"
        },
        "javascript": {
            "extension": ".test.js",
            "pattern": r"^(.*\.test\.js|.*\.spec\.js)$",
            "default": "{module}.test.js"
        },
        "typescript": {
            "extension": ".test.ts",
            "pattern": r"^(.*\.test\.ts|.*\.spec\.ts)$",
            "default": "{module}.test.ts"
        }
    }

    async def execute(self, task: dict, context: AgentContext) -> AgentResult:
        """Execute test generation"""
        is_valid, error = self.validate_input(task)
        if not is_valid:
            return AgentResult(success=False, summary=error, error=error)

        description = task.get("description", "")
        files = task.get("files", [])

        if not files:
            return AgentResult(
                success=False,
                summary="No files provided for test generation",
                error="Please provide files to generate tests for"
            )

        # Detect language and project structure
        language = self._detect_language(files)
        framework = self.TEST_FRAMEWORKS.get(language, self.TEST_FRAMEWORKS["python"])

        # Read existing files for context
        file_contents = {}
        for file_path in files:
            full_path = os.path.join(context.repo_path, file_path)
            if os.path.exists(full_path):
                with open(full_path, 'r') as f:
                    file_contents[file_path] = f.read()

        # Build prompt
        prompt = f"Generate unit tests for:\n\n"
        for path, content in file_contents.items():
            prompt += f"---{path}---\n{content}\n"

        if description:
            prompt += f"\nAdditional requirements: {description}\n"

        # Call Claude
        claude = ClaudeCLI(context.claude_api_key)
        try:
            result = await claude.complete(prompt, self.SYSTEM_PROMPT)

            # Parse and write test files
            test_files = self._parse_test_output(
                result,
                context.repo_path,
                language
            )

            if not test_files:
                return AgentResult(
                    success=False,
                    summary="Failed to parse test output",
                    error="Could not generate valid test files"
                )

            # Write test files
            created_files = []
            for file_path, content in test_files.items():
                full_path = os.path.join(context.repo_path, file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w') as f:
                    f.write(content)
                created_files.append(file_path)

            return AgentResult(
                success=True,
                summary=f"Generated {len(created_files)} test file(s)",
                files_created=created_files
            )

        except Exception as e:
            logger.exception("Test generation failed")
            return await self.on_error(e, task)

    def validate_input(self, task: dict) -> tuple[bool, Optional[str]]:
        """Validate task input"""
        if not task.get("description") and not task.get("files"):
            return False, "Description or files are required"
        return True, None

    def _detect_language(self, files: List[str]) -> str:
        """Detect programming language from files"""
        extensions = {".py": "python", ".js": "javascript", ".ts": "typescript"}

        for file in files:
            ext = os.path.splitext(file)[1]
            if ext in extensions:
                return extensions[ext]

        # Check for package.json or requirements.txt
        for file in files:
            if file.endswith("package.json"):
                return "javascript"
            if file.endswith("requirements.txt") or "requirements" in file:
                return "python"

        return "python"  # Default

    def _parse_test_output(self, output: str, repo_path: str, language: str) -> dict:
        """Parse test files from Claude output"""
        test_files = {}
        current_file = None
        current_content = []

        framework = self.TEST_FRAMEWORKS.get(language, self.TEST_FRAMEWORKS["python"])

        for line in output.split('\n'):
            if line.startswith('---FILE:'):
                # Save previous file
                if current_file:
                    test_files[current_file] = '\n'.join(current_content)

                # Extract filename
                current_file = line.replace('---FILE:', '').replace('---', '').strip()

                # Ensure correct extension
                if not re.match(framework["pattern"], current_file):
                    base = os.path.splitext(current_file)[0]
                    current_file = base + framework["extension"]

                current_content = []
            elif current_file:
                current_content.append(line)
            else:
                # No file specified - try to determine from content
                if line.strip():
                    # First non-file content - create default test file
                    current_file = framework["default"].format(module="test")
                    current_content = [line]

        # Save last file
        if current_file and current_content:
            test_files[current_file] = '\n'.join(current_content)

        return test_files

    def get_required_files(self, task: dict) -> list[str]:
        """Return list of files agent needs to read"""
        return task.get("files", [])
