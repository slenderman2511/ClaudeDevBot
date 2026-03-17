# .claudebot/agents/code_agent.py
"""Code generation agent"""

import os
import logging
from typing import Optional

from .base_agent import BaseAgent, AgentContext, AgentResult
from ..tools.claude_cli import ClaudeCLI

logger = logging.getLogger(__name__)

class CodeAgent(BaseAgent):
    """Agent for generating code from descriptions"""

    name = "code"
    description = "Generate code from descriptions"

    SYSTEM_PROMPT = """You are an expert software developer. Generate code based on the user's description.

Rules:
1. Only output the code, no explanations
2. Use appropriate language/framework based on existing files
3. Follow best practices and coding standards
4. If multiple files are needed, separate them with ---FILE:filename---"""

    async def execute(self, task: dict, context: AgentContext) -> AgentResult:
        """Execute code generation"""
        is_valid, error = self.validate_input(task)
        if not is_valid:
            return AgentResult(success=False, summary=error, error=error)

        description = task.get("description", "")
        files = task.get("files", [])

        # Read existing files for context
        file_contents = {}
        for file_path in files:
            full_path = os.path.join(context.repo_path, file_path)
            if os.path.exists(full_path):
                with open(full_path, 'r') as f:
                    file_contents[file_path] = f.read()

        # Build context prompt
        context_prompt = f"Generate code for: {description}\n\n"
        if file_contents:
            context_prompt += "Existing files:\n"
            for path, content in file_contents.items():
                context_prompt += f"\n---{path}---\n{content}\n"

        # Call Claude
        claude = ClaudeCLI(context.claude_api_key)
        try:
            result = await claude.complete(context_prompt, self.SYSTEM_PROMPT)

            # Parse and write files
            modified_files = []
            current_file = None
            current_content = []

            for line in result.split('\n'):
                if line.startswith('---FILE:'):
                    if current_file and current_content:
                        file_path = os.path.join(context.repo_path, current_file)
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        with open(file_path, 'w') as f:
                            f.write('\n'.join(current_content))
                        modified_files.append(current_file)
                    current_file = line.replace('---FILE:', '').replace('---', '').strip()
                    current_content = []
                elif current_file:
                    current_content.append(line)
                else:
                    # Single file output (backwards compatible)
                    if not current_file and file_contents:
                        # Modify first existing file
                        current_file = files[0] if files else "output.py"
                        current_content = [line]

            # Write last file
            if current_file and current_content:
                file_path = os.path.join(context.repo_path, current_file)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w') as f:
                    f.write('\n'.join(current_content))
                if current_file not in modified_files:
                    modified_files.append(current_file)

            return AgentResult(
                success=True,
                summary=f"Generated {len(modified_files)} file(s)",
                files_modified=modified_files
            )

        except Exception as e:
            logger.exception("Code generation failed")
            return await self.on_error(e, task)

    def validate_input(self, task: dict) -> tuple[bool, Optional[str]]:
        """Validate task input"""
        if not task.get("description"):
            return False, "Description is required"
        return True, None
