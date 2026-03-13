"""
Spec Graph Engine Module

Handles specification loading, validation, and graph representation.
"""

import os
import re
import yaml
import logging
from typing import Any, Dict, List, Optional, Set
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class TaskPhase(Enum):
    """Development phases."""
    DESIGN = "design"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    DEPLOYMENT = "deployment"


@dataclass
class SpecTask:
    """Represents a single task in a specification."""

    id: str
    name: str
    description: str = ""
    phase: TaskPhase = TaskPhase.IMPLEMENTATION
    status: TaskStatus = TaskStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    assignee: str = ""  # Agent type
    estimated_hours: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def can_execute(self, completed_tasks: Set[str]) -> bool:
        """Check if all dependencies are met."""
        return all(dep in completed_tasks for dep in self.dependencies)


@dataclass
class SpecFeature:
    """Represents a complete feature specification."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    status: str = "draft"
    tasks: List[SpecTask] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    file_path: str = ""

    def get_tasks_by_phase(self, phase: TaskPhase) -> List[SpecTask]:
        """Get all tasks in a specific phase."""
        return [t for t in self.tasks if t.phase == phase]

    def get_pending_tasks(self) -> List[SpecTask]:
        """Get all pending tasks."""
        return [t for t in self.tasks if t.status == TaskStatus.PENDING]

    def get_completed_tasks(self) -> List[SpecTask]:
        """Get all completed tasks."""
        return [t for t in self.tasks if t.status == TaskStatus.COMPLETED]


class SpecGraph:
    """
    Directed Acyclic Graph (DAG) of tasks.

    Represents the dependency relationships between tasks.
    """

    def __init__(self, feature: SpecFeature):
        self.feature = feature
        self._adjacency: Dict[str, List[str]] = {}  # task_id -> dependent tasks
        self._reverse_adj: Dict[str, List[str]] = {}  # task_id -> dependencies
        self._build_graph()

    def _build_graph(self):
        """Build the graph from tasks."""
        # Initialize
        for task in self.feature.tasks:
            self._adjacency[task.id] = []
            self._reverse_adj[task.id] = task.dependencies

        # Build edges
        for task in self.feature.tasks:
            for dep in task.dependencies:
                if dep in self._adjacency:
                    self._adjacency[dep].append(task.id)

    def get_ready_tasks(self, completed: Set[str]) -> List[SpecTask]:
        """Get tasks ready to execute (dependencies met)."""
        ready = []
        for task in self.feature.tasks:
            if task.status == TaskStatus.PENDING and task.can_execute(completed):
                ready.append(task)
        return ready

    def get_execution_levels(self) -> List[List[SpecTask]]:
        """
        Get tasks grouped by execution level.

        Tasks in the same level can run in parallel.
        """
        # Group by phase for simplicity
        phase_groups: Dict[TaskPhase, List[SpecTask]] = {}
        for task in self.feature.tasks:
            if task.status != TaskStatus.COMPLETED:
                if task.phase not in phase_groups:
                    phase_groups[task.phase] = []
                phase_groups[task.phase].append(task)

        # Order phases
        phase_order = [TaskPhase.DESIGN, TaskPhase.IMPLEMENTATION, TaskPhase.TESTING, TaskPhase.DEPLOYMENT]
        levels = []
        for phase in phase_order:
            if phase in phase_groups and phase_groups[phase]:
                levels.append(phase_groups[phase])

        return levels

    def get_parallel_groups(self) -> List[List[SpecTask]]:
        """Alias for get_execution_levels."""
        return self.get_execution_levels()

    def topological_sort(self) -> List[SpecTask]:
        """Get tasks in topological order."""
        result = []
        visited: Set[str] = set()
        temp_mark: Set[str] = set()

        def visit(task: SpecTask):
            if task.id in temp_mark:
                raise ValueError(f"Circular dependency detected: {task.id}")
            if task.id in visited:
                return

            temp_mark.add(task.id)

            for dep_id in task.dependencies:
                dep = next((t for t in self.feature.tasks if t.id == dep_id), None)
                if dep:
                    visit(dep)

            temp_mark.remove(task.id)
            visited.add(task.id)
            result.append(task)

        for task in self.feature.tasks:
            if task.id not in visited:
                visit(task)

        return result


class SpecEngine:
    """
    Specification Engine.

    Loads, validates, and manages feature specifications.
    """

    def __init__(self, base_path: str = "openspec"):
        """
        Initialize the spec engine.

        Args:
            base_path: Base path for OpenSpec directory
        """
        self.base_path = Path(base_path)
        self.features_path = self.base_path / "features"
        self.context_path = self.base_path / "context"
        self.plans_path = self.base_path / "plans"

        # Ensure directories exist
        self.features_path.mkdir(parents=True, exist_ok=True)
        self.context_path.mkdir(parents=True, exist_ok=True)
        self.plans_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"SpecEngine initialized with base path: {base_path}")

    def load_feature(self, name: str) -> Optional[SpecFeature]:
        """
        Load a feature specification.

        Args:
            name: Feature name

        Returns:
            SpecFeature or None if not found
        """
        # Try .md file
        md_path = self.features_path / f"{name}.md"
        if md_path.exists():
            return self._parse_markdown(md_path)

        # Try YAML
        yaml_path = self.features_path / f"{name}.yaml"
        if yaml_path.exists():
            return self._parse_yaml(yaml_path)

        # Try directory
        dir_path = self.features_path / name
        if dir_path.is_dir():
            return self._parse_directory(dir_path)

        logger.warning(f"Feature not found: {name}")
        return None

    def _parse_markdown(self, path: Path) -> SpecFeature:
        """Parse markdown specification file."""
        content = path.read_text()
        lines = content.split("\n")

        feature = SpecFeature(
            name=path.stem,
            file_path=str(path)
        )

        current_phase = TaskPhase.IMPLEMENTATION
        task_id = 0

        for line in lines:
            line = line.strip()

            # Parse header fields
            if line.startswith("## Status"):
                continue
            elif line.lower() in ["draft", "active", "completed", "deprecated"]:
                feature.status = line.lower()

            elif line.startswith("## Version"):
                continue

            # Parse phase - handles "### Phase 1: Design" or "### Phase: Design"
            if line.lower().startswith("### phase") or "phase" in line.lower():
                phase_text = line.lower()
                if "design" in phase_text:
                    current_phase = TaskPhase.DESIGN
                elif "implement" in phase_text:
                    current_phase = TaskPhase.IMPLEMENTATION
                elif "test" in phase_text or "testing" in phase_text:
                    current_phase = TaskPhase.TESTING
                elif "deploy" in phase_text or "deployment" in phase_text:
                    current_phase = TaskPhase.DEPLOYMENT

            # Parse task
            elif line.startswith("- [") and current_phase:
                completed = line.startswith("- [x]")
                task_name = line[5:].strip()

                task = SpecTask(
                    id=f"task_{task_id}",
                    name=task_name,
                    description=task_name,
                    phase=current_phase,
                    status=TaskStatus.COMPLETED if completed else TaskStatus.PENDING,
                    assignee=self._infer_assignee(current_phase)
                )
                feature.tasks.append(task)
                task_id += 1

        return feature

    def _parse_yaml(self, path: Path) -> SpecFeature:
        """Parse YAML specification file."""
        data = yaml.safe_load(path.read_text())

        feature = SpecFeature(
            name=data.get("name", path.stem),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            status=data.get("status", "draft"),
            file_path=str(path)
        )

        # Parse tasks
        task_id = 0
        for phase_name, tasks in data.get("tasks", {}).items():
            phase = self._parse_phase(phase_name)

            for task_data in tasks:
                task = SpecTask(
                    id=task_data.get("id", f"task_{task_id}"),
                    name=task_data.get("name", ""),
                    description=task_data.get("description", ""),
                    phase=phase,
                    status=TaskStatus.COMPLETED if task_data.get("completed") else TaskStatus.PENDING,
                    dependencies=task_data.get("depends_on", []),
                    assignee=task_data.get("assignee", self._infer_assignee(phase))
                )
                feature.tasks.append(task)
                task_id += 1

        return feature

    def _parse_directory(self, path: Path) -> SpecFeature:
        """Parse feature from directory."""
        # Look for spec.md or spec.yaml
        spec_file = path / "spec.md"
        if not spec_file.exists():
            spec_file = path / "spec.yaml"

        if spec_file.suffix == ".yaml":
            return self._parse_yaml(spec_file)
        else:
            return self._parse_markdown(spec_file)

    def _parse_phase(self, phase_name: str) -> TaskPhase:
        """Parse phase name to enum."""
        name_lower = phase_name.lower()
        if "design" in name_lower:
            return TaskPhase.DESIGN
        elif "implement" in name_lower:
            return TaskPhase.IMPLEMENTATION
        elif "test" in name_lower:
            return TaskPhase.TESTING
        elif "deploy" in name_lower:
            return TaskPhase.DEPLOYMENT
        return TaskPhase.IMPLEMENTATION

    def _infer_assignee(self, phase: TaskPhase) -> str:
        """Infer which agent should handle this phase."""
        mapping = {
            TaskPhase.DESIGN: "spec_agent",
            TaskPhase.IMPLEMENTATION: "code_agent",
            TaskPhase.TESTING: "test_agent",
            TaskPhase.DEPLOYMENT: "deploy_agent"
        }
        return mapping.get(phase, "code_agent")

    def create_feature(self, name: str, description: str = "") -> SpecFeature:
        """Create a new feature specification."""
        feature = SpecFeature(
            name=name,
            description=description,
            status="draft"
        )

        # Add default tasks based on phases
        for phase in TaskPhase:
            for i in range(2):
                task = SpecTask(
                    id=f"task_{phase.value}_{i}",
                    name=f"{phase.value.title()} Task {i+1}",
                    phase=phase,
                    assignee=self._infer_assignee(phase)
                )
                feature.tasks.append(task)

        # Save to file
        self._save_feature(feature)

        return feature

    def _save_feature(self, feature: SpecFeature):
        """Save feature to file."""
        path = self.features_path / f"{feature.name}.md"

        content = f"""# Feature: {feature.name}

## Overview
{feature.description}

## Version
{feature.version}

## Status
{feature.status}

## Tasks
"""

        # Group by phase
        current_phase = None
        for task in feature.tasks:
            if task.phase != current_phase:
                current_phase = task.phase
                content += f"\n### Phase: {current_phase.value.title()}\n"

            status = "x" if task.status == TaskStatus.COMPLETED else " "
            content += f"- [{status}] {task.name}\n"

        path.write_text(content)
        logger.info(f"Saved feature: {feature.name}")

    def list_features(self) -> List[str]:
        """List all available features."""
        features = []
        if self.features_path.exists():
            for f in self.features_path.glob("*.md"):
                if f.stem != "feature-template":
                    features.append(f.stem)
        return features

    def get_task_graph(self, feature_name: str) -> Optional[SpecGraph]:
        """Get task graph for a feature."""
        feature = self.load_feature(feature_name)
        if feature:
            return SpecGraph(feature)
        return None

    def validate_feature(self, feature: SpecFeature) -> Dict[str, Any]:
        """Validate a feature specification."""
        errors = []
        warnings = []

        if not feature.tasks:
            errors.append("No tasks defined")

        # Check for circular dependencies
        try:
            graph = SpecGraph(feature)
            graph.topological_sort()
        except ValueError as e:
            errors.append(str(e))

        # Check task balance
        total = len(feature.tasks)
        completed = len(feature.get_completed_tasks())
        if total > 0 and completed == total:
            warnings.append("All tasks completed - consider marking feature as completed")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "stats": {
                "total_tasks": total,
                "completed_tasks": completed,
                "pending_tasks": total - completed,
                "progress": f"{(completed/total*100):.1f}%" if total > 0 else "0%"
            }
        }


# Global instance
_spec_engine: Optional[SpecEngine] = None


def get_spec_engine(base_path: str = "openspec") -> SpecEngine:
    """Get the global spec engine instance."""
    global _spec_engine
    if _spec_engine is None:
        _spec_engine = SpecEngine(base_path)
    return _spec_engine
