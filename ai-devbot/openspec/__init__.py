"""
OpenSpec Module

Manages feature specifications, task tracking, and context for
Spec-Driven AI Development.
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class SpecStatus:
    """Specification status constants."""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    DEPRECATED = "deprecated"


class OpenSpec:
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
        """
        Load a feature specification.

        Args:
            name: Feature name

        Returns:
            Feature spec dict or None if not found
        """
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
            "status": SpecStatus.DRAFT,
            "version": "1.0.0"
        }

        # Parse markdown sections
        lines = content.split("\n")
        in_tasks = False
        current_phase = ""

        for line in lines:
            line = line.strip()

            # Parse key-value sections
            if line.startswith("## "):
                section = line[3:].lower()
                in_tasks = section == "tasks"

            elif line.startswith("## Status"):
                # Look for status in next lines
                continue
            elif spec.get("status") == SpecStatus.DRAFT and line.lower() in ["draft", "active", "completed", "deprecated"]:
                spec["status"] = line.lower()

            elif line.startswith("## Version"):
                continue
            elif "version" in spec and line.strip():
                # Try to extract version
                version_match = re.search(r'\d+\.\d+\.\d+', line)
                if version_match:
                    spec["version"] = version_match.group()

            elif line.startswith("## Dependencies"):
                continue
            elif spec.get("dependencies") == [] and line.strip() and not line.startswith("-"):
                deps = [d.strip() for d in line.split(",")]
                spec["dependencies"] = [d for d in deps if d]

            # Parse tasks
            if in_tasks:
                # Phase headers
                if line.startswith("### "):
                    current_phase = line[4:].strip()
                # Task items
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
        """
        Create a new feature specification.

        Args:
            name: Feature name
            description: Feature description
            version: Version string

        Returns:
            Created feature spec
        """
        template_file = self.features_path / "feature-template.md"
        if template_file.exists():
            template = template_file.read_text()
            content = template.replace("{{feature_name}}", name)
            content = content.replace("{{feature_description}}", description)
            content = content.replace("{{version}}", version)
        else:
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
        """
        Update task completion status.

        Args:
            feature_name: Feature name
            task_name: Task name
            completed: Completion status

        Returns:
            True if updated successfully
        """
        spec = self.load_feature(feature_name)
        if not spec:
            return False

        spec_file = Path(spec["file"])
        content = spec_file.read_text()

        # Find and update task
        check_mark = 'x' if completed else ' '
        task_pattern = f"- [{check_mark}] {task_name}"
        if task_name not in content:
            logger.warning(f"Task not found: {task_name}")
            return False

        replacement = f"- [{check_mark}] {task_name}"
        content = content.replace(task_pattern, replacement)
        spec_file.write_text(content)

        # Clear cache
        if feature_name in self._specs:
            del self._specs[feature_name]

        return True

    def get_pending_tasks(self, feature_name: str) -> List[Dict[str, str]]:
        """
        Get all pending tasks for a feature.

        Args:
            feature_name: Feature name

        Returns:
            List of pending task dicts
        """
        spec = self.load_feature(feature_name)
        if not spec:
            return []

        return [
            {"name": t["name"], "phase": t["phase"]}
            for t in spec["tasks"]
            if not t["completed"]
        ]

    def get_task_graph(self, feature_name: str) -> Dict[str, Any]:
        """
        Generate task graph from feature spec.

        Args:
            feature_name: Feature name

        Returns:
            Task graph with phases and dependencies
        """
        spec = self.load_feature(feature_name)
        if not spec:
            return {"error": "Feature not found"}

        # Group tasks by phase
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
        """
        Validate a feature specification.

        Args:
            name: Feature name

        Returns:
            Validation result with errors/warnings
        """
        spec = self.load_feature(name)
        if not spec:
            return {"valid": False, "errors": ["Feature not found"]}

        errors = []
        warnings = []

        # Check required fields
        if not spec.get("tasks"):
            errors.append("No tasks defined")

        # Check task completion balance
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


# Default instance
_default_spec: Optional[OpenSpec] = None


def get_openspec(base_path: str = "openspec") -> OpenSpec:
    """Get default OpenSpec instance."""
    global _default_spec
    if _default_spec is None:
        _default_spec = OpenSpec(base_path)
    return _default_spec
