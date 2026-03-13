"""
DevBot Core Module

Main DevBot class that orchestrates all components.
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from devbot.observability.logger import get_logger
from devbot.scanner.project_scanner import ProjectScanner
from devbot.scanner.stack_detector import StackDetector
from devbot.graph.code_graph_builder import CodeGraphBuilder
from devbot.spec.openspec_sync import OpenSpecSync
from devbot.spec.spec_generator import SpecGenerator
from devbot.agents.planner_agent import PlannerAgent
from devbot.agents.code_agent import CodeAgent
from devbot.agents.test_agent import TestAgent
from devbot.agents.deploy_agent import DeployAgent
from devbot.orchestrator.executor import Executor
from devbot.tools.claude_cli import ClaudeCLITool
from devbot.tools.git_tools import GitTool

logger = get_logger(__name__)


class DevBot:
    """
    Main DevBot class that orchestrates all components.

    Provides:
    - Project scanning and analysis
    - OpenSpec integration
    - AI agent execution
    - Code generation
    - Git operations
    """

    def __init__(self, project_path: str = ".", config: Optional[Dict[str, Any]] = None):
        """
        Initialize DevBot.

        Args:
            project_path: Path to the project directory
            config: Optional configuration dictionary
        """
        self.project_path = Path(project_path).resolve()
        self.config = config or {}
        self.devbot_dir = self.project_path / ".devbot"

        # Initialize components
        self._init_components()

        logger.info(f"DevBot initialized for: {self.project_path}")

    def _init_components(self):
        """Initialize all DevBot components."""
        # Observability
        from devbot.observability import setup_tracing
        setup_tracing(self.config.get('tracing', True))

        # Scanner
        self.scanner = ProjectScanner(str(self.project_path))
        self.stack_detector = StackDetector(str(self.project_path))

        # Code Graph
        self.graph_builder = CodeGraphBuilder(str(self.project_path))

        # OpenSpec
        openspec_path = self.config.get('openspec_path', str(self.project_path / "openspec"))
        self.openspec = OpenSpecSync(openspec_path)

        # Spec Generator
        claude_config = self.config.get('claude', {})
        claude_config['project_context'] = str(self.project_path)
        self.claude_tool = ClaudeCLITool(claude_config)
        self.spec_generator = SpecGenerator(self.claude_tool)

        # Git tool
        git_config = self.config.get('git', {})
        git_config['repo_path'] = str(self.project_path)
        self.git_tool = GitTool(git_config)

        # Agents
        self.planner = PlannerAgent(
            config=self.config.get('planner', {}),
            openspec=self.openspec
        )
        self.code_agent = CodeAgent(
            config=self.config.get('code', {}),
            claude_tool=self.claude_tool,
            openspec=self.openspec
        )
        self.test_agent = TestAgent(
            config=self.config.get('test', {})
        )
        self.deploy_agent = DeployAgent(
            config=self.config.get('deploy', {})
        )

        # Executor
        self.executor = Executor(
            max_workers=self.config.get('max_workers', 4),
            retry_attempts=self.config.get('retry_attempts', 3)
        )
        self.executor.register_agent('code', self.code_agent)
        self.executor.register_agent('test', self.test_agent)
        self.executor.register_agent('deploy', self.deploy_agent)

    # ========== ATTACH COMMAND ==========

    def attach(self) -> Dict[str, Any]:
        """
        Attach to a repository - initialize .devbot folder and create project profile.

        Returns:
            Result dictionary
        """
        logger.info("Attaching to project...")

        # Create .devbot directory
        self.devbot_dir.mkdir(exist_ok=True)

        # Save project profile
        profile = {
            "path": str(self.project_path),
            "name": self.project_path.name,
            "attached_at": self._get_timestamp()
        }

        profile_file = self.devbot_dir / "project_profile.json"
        profile_file.write_text(json.dumps(profile, indent=2))

        # Save state
        state = {
            "attached": True,
            "version": "1.0.0"
        }
        state_file = self.devbot_dir / "devbot_state.json"
        state_file.write_text(json.dumps(state, indent=2))

        logger.info(f"Attached to project: {self.project_path.name}")
        return {"success": True, "project": profile}

    # ========== SCAN COMMAND ==========

    def scan(self) -> Dict[str, Any]:
        """
        Scan the project - detect tech stack, identify framework, map modules.

        Returns:
            Scan results dictionary
        """
        logger.info("Scanning project...")

        # Scan project structure
        project_info = self.scanner.scan()

        # Detect stack
        stack_info = self.stack_detector.detect()

        # Combine results
        result = {
            "project": project_info,
            "stack": stack_info
        }

        # Save to .devbot
        self.devbot_dir.mkdir(exist_ok=True)
        profile_file = self.devbot_dir / "project_profile.json"
        profile_file.write_text(json.dumps(result, indent=2))

        logger.info(f"Scan complete: {project_info.get('name')}")
        return result

    # ========== GRAPH COMMAND ==========

    def build_graph(self) -> Dict[str, Any]:
        """
        Build a code knowledge graph.

        Returns:
            Graph data
        """
        logger.info("Building code graph...")

        graph = self.graph_builder.build()
        self.devbot_dir.mkdir(exist_ok=True)
        graph_file = self.devbot_dir / "code_graph.json"
        graph_file.write_text(json.dumps(graph, indent=2))

        logger.info(f"Graph built: {len(graph.get('nodes', {}))} nodes")
        return graph

    # ========== FEATURE COMMAND ==========

    def create_feature(self, feature_name: str, description: str = "") -> Dict[str, Any]:
        """
        Create a new feature specification.

        Args:
            feature_name: Name of the feature
            description: Description of the feature

        Returns:
            Created feature data
        """
        logger.info(f"Creating feature: {feature_name}")

        # Generate spec with tasks
        spec = self.spec_generator.generate(feature_name, description)

        # Generate markdown content with tasks
        md_content = self.spec_generator.generate_markdown(feature_name, description)

        # Save to openspec/features/
        feature_file = self.openspec.features_path / f"{feature_name}.md"
        feature_file.write_text(md_content)

        return {
            "success": True,
            "feature": feature_name,
            "file": str(feature_file)
        }

    # ========== PLAN COMMAND ==========

    def plan_feature(self, feature_name: str) -> Dict[str, Any]:
        """
        Plan a feature - generate task DAG from OpenSpec.

        Args:
            feature_name: Name of the feature to plan

        Returns:
            Plan results
        """
        logger.info(f"Planning feature: {feature_name}")

        # Load feature
        feature = self.openspec.load_feature(feature_name)
        if not feature:
            return {"success": False, "error": f"Feature '{feature_name}' not found"}

        # Generate task graph via planner agent
        from devbot.agents.base_agent import Task
        task = Task(input=feature_name)
        result = self.planner.execute(task)

        if result.success:
            # Save plan
            plan_file = self.openspec.plans_path / f"{feature_name}-plan.md"
            plan_file.write_text(result.output)

            return {
                "success": True,
                "feature": feature_name,
                "plan": result.output,
                "plan_file": str(plan_file)
            }

        return {
            "success": False,
            "error": result.error
        }

    # ========== IMPLEMENT COMMAND ==========

    async def implement_feature(self, feature_name: str) -> Dict[str, Any]:
        """
        Implement a feature - spawn agents and generate code.

        Args:
            feature_name: Name of the feature to implement

        Returns:
            Implementation results
        """
        logger.info(f"Implementing feature: {feature_name}")

        # Load feature and plan
        feature = self.openspec.load_feature(feature_name)
        if not feature:
            return {"success": False, "error": f"Feature '{feature_name}' not found"}

        # Get pending tasks
        pending_tasks = self.openspec.get_pending_tasks(feature_name)

        if not pending_tasks:
            return {"success": False, "error": "No pending tasks to implement"}

        # Execute via executor
        from devbot.orchestrator.task_graph import create_task_graph
        task_graph = create_task_graph(
            feature_name,
            [{"name": t["name"], "phase": t["phase"], "agent_type": "code"} for t in pending_tasks]
        )

        result = await self.executor.execute(task_graph)

        return {
            "success": result.get("success", False),
            "feature": feature_name,
            "completed_tasks": result.get("completed_tasks", 0),
            "failed_tasks": result.get("failed_tasks", 0)
        }

    # ========== UTILITY METHODS ==========

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()

    def get_status(self) -> Dict[str, Any]:
        """Get DevBot status."""
        return {
            "project_path": str(self.project_path),
            "attached": (self.devbot_dir / "devbot_state.json").exists(),
            "claude_available": self.claude_tool.validate(),
            "git_available": self.git_tool.validate()
        }


def create_devbot(project_path: str = ".", config: Optional[Dict[str, Any]] = None) -> DevBot:
    """
    Create a DevBot instance.

    Args:
        project_path: Path to the project
        config: Optional configuration

    Returns:
        DevBot instance
    """
    return DevBot(project_path, config)
