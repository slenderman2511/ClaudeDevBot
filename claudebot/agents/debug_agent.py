# .claudebot/agents/debug_agent.py
"""Debug agent for analyzing errors and suggesting fixes"""

import os
import re
import logging
from typing import Optional, List, Dict

from .base_agent import BaseAgent, AgentContext, AgentResult
from ..tools.claude_cli import ClaudeCLI

logger = logging.getLogger(__name__)


class DebugAgent(BaseAgent):
    """Agent for debugging and fixing errors"""

    name = "debug"
    description = "Analyze errors and suggest code fixes"

    SYSTEM_PROMPT = """You are an expert software developer specializing in debugging.
Analyze the provided error and code to identify the root cause and suggest fixes.

Your response should include:
1. Root cause analysis - what exactly is causing the error
2. Suggested fix - concrete code changes to fix the issue
3. Prevention tips - how to avoid this issue in the future

Output format:
- For code changes, use ---FILE:filepath--- to indicate which file to modify
- Use ---FIX:filepath--- for the fixed version of the file
- Provide clear explanations"""

    ERROR_PATTERNS = {
        "python": {
            "syntax": r"SyntaxError: (.+)",
            "import": r"ImportError: (.+)|ModuleNotFoundError: (.+)",
            "type": r"TypeError: (.+)",
            "attribute": r"AttributeError: (.+)",
            "name": r"NameError: (.+)",
            "index": r"IndexError: (.+)",
            "key": r"KeyError: (.+)",
            "value": r"ValueError: (.+)",
            "runtime": r"RuntimeError: (.+)",
        },
        "javascript": {
            "syntax": r"SyntaxError: (.+)",
            "reference": r"ReferenceError: (.+)",
            "type": r"TypeError: (.+)",
            "range": r"RangeError: (.+)",
        }
    }

    async def execute(self, task: dict, context: AgentContext) -> AgentResult:
        """Execute debug analysis"""
        is_valid, error = self.validate_input(task)
        if not is_valid:
            return AgentResult(success=False, summary=error, error=error)

        description = task.get("description", "")
        error_msg = task.get("error", "")
        files = task.get("files", [])

        # If no explicit error, try to extract from description
        if not error_msg:
            error_msg = self._extract_error_from_description(description)

        # Read relevant files for context
        file_contents = {}
        for file_path in files:
            full_path = os.path.join(context.repo_path, file_path)
            if os.path.exists(full_path):
                with open(full_path, 'r') as f:
                    file_contents[file_path] = f.read()

        # Detect language
        language = self._detect_language(files)

        # Build prompt
        prompt = "Analyze and fix the following error:\n\n"
        if error_msg:
            prompt += f"Error: {error_msg}\n\n"

        if description:
            prompt += f"Description: {description}\n\n"

        if file_contents:
            prompt += "Relevant code:\n"
            for path, content in file_contents.items():
                prompt += f"---{path}---\n{content}\n"

        # Call Claude
        claude = ClaudeCLI(context.claude_api_key)
        try:
            result = await claude.complete(prompt, self.SYSTEM_PROMPT)

            # Parse fix from output
            fixes = self._parse_fix_output(result, context.repo_path, file_contents)

            if not fixes:
                # No file changes, just return the analysis
                return AgentResult(
                    success=True,
                    summary="Analysis complete",
                    logs=[result]
                )

            # Apply fixes
            created_files = []
            modified_files = []
            for file_path, content in fixes.items():
                full_path = os.path.join(context.repo_path, file_path)
                exists = os.path.exists(full_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w') as f:
                    f.write(content)
                if exists:
                    modified_files.append(file_path)
                else:
                    created_files.append(file_path)

            summary = []
            if created_files:
                summary.append(f"Created {len(created_files)} file(s)")
            if modified_files:
                summary.append(f"Fixed {len(modified_files)} file(s)")

            return AgentResult(
                success=True,
                summary=". ".join(summary) if summary else "Debug analysis complete",
                files_created=created_files,
                files_modified=modified_files,
                logs=[result]
            )

        except Exception as e:
            logger.exception("Debug analysis failed")
            return await self.on_error(e, task)

    def validate_input(self, task: dict) -> tuple[bool, Optional[str]]:
        """Validate task input"""
        if not task.get("description") and not task.get("error"):
            return False, "Description or error message is required"
        return True, None

    def _extract_error_from_description(self, description: str) -> str:
        """Extract error message from description"""
        # Look for common error patterns
        error_indicators = [
            "error:", "exception:", "failed:", "traceback",
            "crash", "broken", "not working"
        ]

        lower_desc = description.lower()
        for indicator in error_indicators:
            if indicator in lower_desc:
                # Try to extract the error part
                idx = lower_desc.find(indicator)
                return description[idx:].split('\n')[0]

        return description

    def _detect_language(self, files: List[str]) -> str:
        """Detect programming language from files"""
        extensions = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "javascript",
            ".jsx": "javascript",
            ".tsx": "javascript"
        }

        for file in files:
            ext = os.path.splitext(file)[1]
            if ext in extensions:
                return extensions[ext]

        return "python"  # Default

    def _parse_fix_output(self, output: str, repo_path: str, original_files: Dict[str, str]) -> Dict[str, str]:
        """Parse fixes from Claude output"""
        fixes = {}
        current_file = None
        current_content = []
        mode = "content"  # content or fix

        for line in output.split('\n'):
            if line.startswith('---FIX:'):
                # Save previous file content
                if current_file and current_content:
                    fixes[current_file] = '\n'.join(current_content)
                current_file = line.replace('---FIX:', '').replace('---', '').strip()
                current_content = []
                mode = "fix"
            elif line.startswith('---FILE:'):
                # Just switching file, not a fix block
                if current_file and current_content:
                    fixes[current_file] = '\n'.join(current_content)
                current_file = line.replace('---FILE:', '').replace('---', '').strip()
                current_content = []
                mode = "content"
            elif current_file:
                current_content.append(line)

        # Save last file
        if current_file and current_content:
            fixes[current_file] = '\n'.join(current_content)

        return fixes

    def get_required_files(self, task: dict) -> list[str]:
        """Return list of files agent needs to read"""
        return task.get("files", [])
