"""
Project Scanner Module

Scans a project directory and collects information about the codebase.
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from claudebot.observability.logger import get_logger

logger = get_logger(__name__)


class ProjectScanner:
    """
    Scans a project directory and collects information about the codebase.

    Identifies:
    - Project structure
    - Tech stack
    - Dependencies
    - Configuration files
    """

    def __init__(self, project_path: str = "."):
        """
        Initialize the project scanner.

        Args:
            project_path: Path to the project directory
        """
        self.project_path = Path(project_path).resolve()
        self.project_info: Dict[str, Any] = {}

    def scan(self) -> Dict[str, Any]:
        """
        Scan the project and collect information.

        Returns:
            Dictionary with project information
        """
        logger.info(f"Scanning project at: {self.project_path}")

        self.project_info = {
            "path": str(self.project_path),
            "name": self.project_path.name,
            "scanned_at": datetime.now().isoformat(),
            "structure": self._scan_structure(),
            "language": self._detect_languages(),
            "dependencies": self._scan_dependencies(),
            "config_files": self._find_config_files(),
            "test_files": self._find_test_files(),
            "source_files": self._find_source_files()
        }

        logger.info(f"Project scan complete: {self.project_info.get('name')}")
        return self.project_info

    def _scan_structure(self) -> Dict[str, Any]:
        """Scan project directory structure."""
        structure = {
            "root_files": [],
            "directories": []
        }

        try:
            for item in os.listdir(self.project_path):
                item_path = self.project_path / item
                if item_path.is_file():
                    structure["root_files"].append(item)
                elif item_path.is_dir() and not item.startswith('.'):
                    structure["directories"].append(item)
        except PermissionError:
            logger.warning(f"Permission denied scanning: {self.project_path}")

        return structure

    def _detect_languages(self) -> List[str]:
        """Detect programming languages used in the project."""
        languages = []
        extensions = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.jsx': 'React',
            '.tsx': 'React',
            '.java': 'Java',
            '.go': 'Go',
            '.rs': 'Rust',
            '.rb': 'Ruby',
            '.php': 'PHP',
            '.cs': 'C#',
            '.cpp': 'C++',
            '.c': 'C'
        }

        for root, dirs, files in os.walk(self.project_path):
            # Skip hidden and common non-source directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', '__pycache__', 'build', 'dist']]

            for file in files:
                ext = Path(file).suffix.lower()
                if ext in extensions and extensions[ext] not in languages:
                    languages.append(extensions[ext])

        return languages

    def _scan_dependencies(self) -> Dict[str, Any]:
        """Scan for dependency files."""
        dependencies = {
            "python": {},
            "javascript": {},
            "other": []
        }

        # Python requirements
        req_file = self.project_path / "requirements.txt"
        if req_file.exists():
            try:
                content = req_file.read_text()
                dependencies["python"]["requirements.txt"] = [
                    line.strip() for line in content.split('\n')
                    if line.strip() and not line.startswith('#')
                ]
            except Exception as e:
                logger.warning(f"Failed to read requirements.txt: {e}")

        # Python pyproject.toml
        pyproject = self.project_path / "pyproject.toml"
        if pyproject.exists():
            dependencies["python"]["pyproject.toml"] = "found"

        # Node package.json
        package_json = self.project_path / "package.json"
        if package_json.exists():
            try:
                import json
                with open(package_json) as f:
                    data = json.load(f)
                    dependencies["javascript"]["package.json"] = {
                        "name": data.get("name"),
                        "version": data.get("version"),
                        "dependencies": list(data.get("dependencies", {}).keys())
                    }
            except Exception as e:
                logger.warning(f"Failed to read package.json: {e}")

        # Go go.mod
        go_mod = self.project_path / "go.mod"
        if go_mod.exists():
            dependencies["other"].append("go.mod")

        # Rust Cargo.toml
        cargo = self.project_path / "Cargo.toml"
        if cargo.exists():
            dependencies["other"].append("Cargo.toml")

        return dependencies

    def _find_config_files(self) -> List[str]:
        """Find configuration files."""
        config_patterns = [
            '.gitignore', '.env', '.env.example',
            'config.yaml', 'config.json', 'config.py',
            'setup.py', 'setup.cfg', 'pyproject.toml',
            'docker-compose.yml', 'docker-compose.yaml',
            'Makefile', 'tox.ini', '.flake8', 'pytest.ini'
        ]

        config_files = []
        for pattern in config_patterns:
            if (self.project_path / pattern).exists():
                config_files.append(pattern)

        return config_files

    def _find_test_files(self) -> Dict[str, List[str]]:
        """Find test files by language."""
        test_patterns = {
            'python': ['test_*.py', '*_test.py', 'tests/'],
            'javascript': ['*.test.js', '*.spec.js', '__tests__/'],
            'typescript': ['*.test.ts', '*.spec.ts', '__tests__/']
        }

        test_files = {}

        for lang, patterns in test_patterns.items():
            found = []
            for root, dirs, files in os.walk(self.project_path):
                dirs[:] = [d for d in dirs if not d.startswith('.')]

                for file in files:
                    for pattern in patterns:
                        if pattern.endswith('/'):
                            if pattern.rstrip('/') in root:
                                found.append(os.path.join(root, file))
                        elif self._match_pattern(file, pattern):
                            found.append(os.path.join(root, file))

            if found:
                test_files[lang] = found

        return test_files

    def _find_source_files(self) -> Dict[str, int]:
        """Count source files by extension."""
        counts = {}

        for root, dirs, files in os.walk(self.project_path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', '__pycache__', 'build', 'dist']]

            for file in files:
                ext = Path(file).suffix
                if ext:
                    counts[ext] = counts.get(ext, 0) + 1

        return counts

    def _match_pattern(self, filename: str, pattern: str) -> bool:
        """Simple glob-like pattern matching."""
        import fnmatch
        return fnmatch.fnmatch(filename, pattern)

    def save_profile(self, output_path: Optional[str] = None) -> str:
        """
        Save project profile to file.

        Args:
            output_path: Path to save the profile (default: .devbot/project_profile.json)

        Returns:
            Path to saved file
        """
        if output_path is None:
            devbot_dir = self.project_path / ".devbot"
            devbot_dir.mkdir(exist_ok=True)
            output_path = devbot_dir / "project_profile.json"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(self.project_info, f, indent=2)

        logger.info(f"Project profile saved to: {output_path}")
        return str(output_path)
