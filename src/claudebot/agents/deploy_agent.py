# .claudebot/agents/deploy_agent.py
"""Deployment agent"""

import os
import re
import logging
from typing import Optional, List, Dict
import yaml
import json

from .base_agent import BaseAgent, AgentContext, AgentResult
from ..tools.claude_cli import ClaudeCLI

logger = logging.getLogger(__name__)


class DeployAgent(BaseAgent):
    """Agent for handling deployment workflows"""

    name = "deploy"
    description = "Handle deployment workflows and generate deployment scripts"

    SYSTEM_PROMPT = """You are an expert DevOps engineer.
Generate deployment configurations and scripts for the provided project.

Consider:
1. The existing tech stack and infrastructure
2. Best practices for the target platform (Vercel, AWS, Docker, etc.)
3. Environment variables needed
4. Health checks and monitoring
5. Rollback strategies

Output format:
- For multiple files, separate with ---FILE:filepath---
- Include only the deployment file content, no explanations"""

    DEPLOY_PLATFORMS = {
        "vercel": {
            "config": "vercel.json",
            "script": "deploy-vercel.sh"
        },
        "aws": {
            "config": "cloudformation.yaml",
            "script": "deploy-aws.sh"
        },
        "docker": {
            "config": "Dockerfile",
            "script": "deploy-docker.sh"
        },
        "gcloud": {
            "config": "app.yaml",
            "script": "deploy-gcloud.sh"
        },
        "heroku": {
            "config": "Procfile",
            "script": "deploy-heroku.sh"
        },
        "fly": {
            "config": "Dockerfile",
            "script": "deploy-fly.sh"
        }
    }

    async def execute(self, task: dict, context: AgentContext) -> AgentResult:
        """Execute deployment"""
        is_valid, error = self.validate_input(task)
        if not is_valid:
            return AgentResult(success=False, summary=error, error=error)

        description = task.get("description", "")

        # Detect existing deployment configs
        existing_configs = self._detect_deployment_configs(context.repo_path)

        # Determine target platform
        platform = self._determine_platform(description, existing_configs)

        # Read relevant files for context
        relevant_files = self._get_relevant_files(context.repo_path, platform)
        file_contents = {}
        for file_path in relevant_files:
            full_path = os.path.join(context.repo_path, file_path)
            if os.path.exists(full_path):
                with open(full_path, 'r') as f:
                    file_contents[file_path] = f.read()

        # Build prompt
        prompt = f"Generate deployment configuration for: {description}\n\n"
        prompt += f"Target platform: {platform}\n\n"

        if existing_configs:
            prompt += "Existing deployment configs:\n"
            for path, content in existing_configs.items():
                prompt += f"---{path}---\n{content}\n"

        if file_contents:
            prompt += "\nProject files:\n"
            for path, content in file_contents.items():
                prompt += f"---{path}---\n{content[:2000]}\n"  # Limit size

        # Call Claude
        claude = ClaudeCLI(context.claude_api_key)
        try:
            result = await claude.complete(prompt, self.SYSTEM_PROMPT)

            # Parse and write deployment files
            deploy_files = self._parse_deploy_output(result, platform)

            if not deploy_files:
                return AgentResult(
                    success=False,
                    summary="Failed to parse deployment output",
                    error="Could not generate valid deployment files"
                )

            # Write deployment files
            created_files = []
            modified_files = []
            for file_path, content in deploy_files.items():
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
                summary.append(f"Modified {len(modified_files)} file(s)")

            return AgentResult(
                success=True,
                summary=". ".join(summary) if summary else "Generated deployment configuration",
                files_created=created_files,
                files_modified=modified_files
            )

        except Exception as e:
            logger.exception("Deployment generation failed")
            return await self.on_error(e, task)

    def validate_input(self, task: dict) -> tuple[bool, Optional[str]]:
        """Validate task input"""
        if not task.get("description"):
            return False, "Description is required for deployment"
        return True, None

    def _detect_deployment_configs(self, repo_path: str) -> Dict[str, str]:
        """Detect existing deployment configurations"""
        config_files = [
            "package.json", "requirements.txt", "pyproject.toml",
            "vercel.json", "Dockerfile", "docker-compose.yml",
            "cloudformation.yaml", "app.yaml", "Procfile",
            "fly.toml", ".github/workflows/deploy.yml"
        ]

        configs = {}
        for file_path in config_files:
            full_path = os.path.join(repo_path, file_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r') as f:
                        configs[file_path] = f.read()
                except:
                    pass

        return configs

    def _determine_platform(self, description: str, existing_configs: Dict[str, str]) -> str:
        """Determine target deployment platform"""
        description_lower = description.lower()

        # Check for explicit platform mentions
        platform_keywords = {
            "vercel": ["vercel", "next.js", "nextjs"],
            "aws": ["aws", "amazon", "lambda", "s3", "cloudformation"],
            "docker": ["docker", "container"],
            "gcloud": ["gcloud", "google cloud", "gae", "app engine"],
            "heroku": ["heroku"],
            "fly": ["fly", "fly.io"]
        }

        for platform, keywords in platform_keywords.items():
            if any(kw in description_lower for kw in keywords):
                return platform

        # Detect from existing configs
        if "vercel.json" in existing_configs or "package.json" in existing_configs:
            return "vercel"
        if "Dockerfile" in existing_configs:
            return "docker"
        if "cloudformation.yaml" in existing_configs:
            return "aws"
        if "app.yaml" in existing_configs:
            return "gcloud"
        if "Procfile" in existing_configs:
            return "heroku"

        return "docker"  # Default

    def _get_relevant_files(self, repo_path: str, platform: str) -> List[str]:
        """Get relevant files for deployment context"""
        files = []

        if platform == "vercel":
            files = ["package.json", "next.config.js", "vercel.json"]
        elif platform == "aws":
            files = ["requirements.txt", "setup.py", "cloudformation.yaml"]
        elif platform == "docker":
            files = ["Dockerfile", "docker-compose.yml", "requirements.txt"]
        elif platform == "gcloud":
            files = ["app.yaml", "requirements.txt", "main.py"]
        elif platform == "heroku":
            files = ["Procfile", "requirements.txt", "package.json"]
        elif platform == "fly":
            files = ["Dockerfile", "fly.toml", "requirements.txt"]

        return files

    def _parse_deploy_output(self, output: str, platform: str) -> Dict[str, str]:
        """Parse deployment files from Claude output"""
        deploy_files = {}
        current_file = None
        current_content = []

        for line in output.split('\n'):
            if line.startswith('---FILE:'):
                # Save previous file
                if current_file:
                    deploy_files[current_file] = '\n'.join(current_content)

                # Extract filename
                current_file = line.replace('---FILE:', '').replace('---', '').strip()
                current_content = []
            elif current_file:
                current_content.append(line)
            elif line.strip():
                # No file specified - create based on platform
                if platform in self.DEPLOY_PLATFORMS:
                    current_file = self.DEPLOY_PLATFORMS[platform]["config"]
                    current_content = [line]

        # Save last file
        if current_file and current_content:
            deploy_files[current_file] = '\n'.join(current_content)

        return deploy_files

    def get_required_files(self, task: dict) -> list[str]:
        """Return list of files agent needs to read"""
        return ["package.json", "requirements.txt", "Dockerfile"]
