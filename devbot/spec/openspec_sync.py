"""
OpenSpec Sync Module

Manages feature specifications and syncs with the project.
"""

import os
import re
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from devbot.observability.logger import get_logger

logger = get_logger(__name__)


class OpenSpecSync:
    """
    OpenSpec manager for loading, validating, and managing feature specifications.

    Handles:
    - Loading feature specs from files
    - Task tracking and completion
    - Context management
    - Task graph generation
    """

    def __init__(self, base_path: str = "openspec"):
        """
        Initialize OpenSpec manager.

        Args:
            base_path: Base directory for OpenSpec files
        """
        self.base_path = Path(base_path)
        self.features_path = self.base_path / "features"
        self.context_path = self.base_path / "context"
        self.plans_path = self.base_path / "plans"

        # Ensure directories exist
        self.features_path.mkdir(parents=True, exist_ok=True)
        self.context_path.mkdir(parents=True, exist_ok=True)
        self.plans_path.mkdir(parents=True, exist_ok=True)

        # Cache loaded specs
        self._specs: Dict[str, Dict[str, Any]] = {}

    def list_features(self) -> List[str]:
        """List all available features."""
        features = []
        if self.features_path.exists():
            for f in self.features_path.glob("*.md"):
                if f.stem != "feature-template":
                    features.append(f.stem)
        return features

    def load_feature(self, name: str) -> Optional[Dict[str, Any]]:
        """Load a feature specification."""
        if name in self._specs:
            return self._specs[name]

        spec_file = self.features_path / f"{name}.md"
        if not spec_file.exists():
            logger.warning(f"Feature spec not found: {name}")
            return None

        try:
            spec = self._parse_spec(spec_file)
            self._specs[name] = spec
            return spec
        except Exception as e:
            logger.error(f"Failed to load feature {name}: {e}")
            return None

    def _parse_spec(self, spec_file: Path) -> Dict[str, Any]:
        """Parse a feature spec markdown file."""
        content = spec_file.read_text()

        spec = {
            "name": spec_file.stem,
            "file": str(spec_file),
            "tasks": [],
            "dependencies": [],
            "status": "draft",
            "version": "1.0.0"
        }

        lines = content.split("\n")
        in_tasks = False
        current_phase = ""

        for line in lines:
            line = line.strip()

            if line.startswith("## "):
                section = line[3:].lower()
                in_tasks = section == "tasks"

            elif "version" in spec and line.strip() and not line.startswith("-"):
                version_match = re.search(r'\d+\.\d+\.\d+', line)
                if version_match:
                    spec["version"] = version_match.group()

            # Parse tasks
            if in_tasks:
                if line.startswith("### "):
                    current_phase = line[4:].strip()
                elif line.startswith("- [") and current_phase:
                    checked = line.startswith("- [x]")
                    task_name = line[5:].strip()
                    spec["tasks"].append({
                        "name": task_name,
                        "phase": current_phase,
                        "completed": checked
                    })

        return spec

    def create_feature(self, name: str, description: str, version: str = "1.0.0") -> Dict[str, Any]:
        """Create a new feature specification."""
        content = f"""# Feature: {name}

## Overview
{description}

## Version
{version}

## Status
draft

## Tasks

### Phase 1: Design
- [ ] Design API endpoints
- [ ] Define data models
- [ ] Create database schema

### Phase 2: Implementation
- [ ] Implement core functionality

### Phase 3: Testing
- [ ] Write unit tests
- [ ] Write integration tests

### Phase 4: Deployment
- [ ] Deploy to staging
- [ ] Deploy to production

## Dependencies

## Notes
"""

        spec_file = self.features_path / f"{name}.md"
        spec_file.write_text(content)

        spec = self.load_feature(name)
        logger.info(f"Created feature: {name}")
        return spec

    def update_task_status(self, feature_name: str, task_name: str, completed: bool) -> bool:
        """Update task completion status."""
        spec = self.load_feature(feature_name)
        if not spec:
            return False

        spec_file = Path(spec["file"])
        content = spec_file.read_text()

        check_mark = 'x' if completed else ' '
        task_pattern = f"- [{check_mark}] {task_name}"
        if task_name not in content:
            logger.warning(f"Task not found: {task_name}")
            return False

        replacement = f"- [{check_mark}] {task_name}"
        content = content.replace(task_pattern, replacement)
        spec_file.write_text(content)

        if feature_name in self._specs:
            del self._specs[feature_name]

        return True

    def get_pending_tasks(self, feature_name: str) -> List[Dict[str, str]]:
        """Get all pending tasks for a feature."""
        spec = self.load_feature(feature_name)
        if not spec:
            return []

        return [
            {"name": t["name"], "phase": t["phase"]}
            for t in spec["tasks"]
            if not t["completed"]
        ]

    def get_task_graph(self, feature_name: str) -> Dict[str, Any]:
        """Generate task graph from feature spec."""
        spec = self.load_feature(feature_name)
        if not spec:
            return {"error": "Feature not found"}

        phases = {}
        for task in spec["tasks"]:
            phase = task["phase"]
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(task)

        return {
            "feature": feature_name,
            "version": spec.get("version", "1.0.0"),
            "status": spec.get("status", "draft"),
            "phases": phases,
            "total_tasks": len(spec["tasks"]),
            "completed_tasks": sum(1 for t in spec["tasks"] if t["completed"]),
            "dependencies": spec.get("dependencies", [])
        }

    def get_context(self) -> Dict[str, Any]:
        """Load project context."""
        context = {}
        if self.context_path.exists():
            for ctx_file in self.context_path.glob("*.md"):
                context[ctx_file.stem] = ctx_file.read_text()
        return context

    def validate_spec(self, name: str) -> Dict[str, Any]:
        """Validate a feature specification."""
        spec = self.load_feature(name)
        if not spec:
            return {"valid": False, "errors": ["Feature not found"]}

        errors = []
        warnings = []

        if not spec.get("tasks"):
            errors.append("No tasks defined")

        total = len(spec["tasks"])
        completed = sum(1 for t in spec["tasks"] if t["completed"])
        if total > 0 and completed == total:
            warnings.append("All tasks completed - consider marking feature as completed")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "stats": {
                "total_tasks": total,
                "completed_tasks": completed,
                "progress": f"{(completed/total*100):.1f}%" if total > 0 else "0%"
            }
        }

    def save_plan(self, feature_name: str, plan_content: str) -> str:
        """Save a plan for a feature."""
        plan_file = self.plans_path / f"{feature_name}-plan.md"
        plan_file.write_text(plan_content)
        logger.info(f"Plan saved: {plan_file}")
        return str(plan_file)


def get_openspec(base_path: str = "openspec") -> OpenSpecSync:
    """Get an OpenSpecSync instance."""
    return OpenSpecSync(base_path)
