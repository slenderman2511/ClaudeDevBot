"""
Stack Detector Module

Detects the technology stack used in a project.
"""

import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from devbot.observability.logger import get_logger

logger = get_logger(__name__)


class StackDetector:
    """
    Detects the technology stack used in a project.

    Identifies frameworks, libraries, and tools based on:
    - Dependency files
    - Configuration files
    - Source code patterns
    """

    # Known framework patterns
    FRAMEWORKS = {
        'python': {
            'django': ['settings.py', 'manage.py', 'wsgi.py'],
            'flask': ['app.py', 'wsgi.py'],
            'fastapi': ['main.py'],
            'pyramid': ['__init__.py'],
            'tornado': ['application.py'],
            'pytest': ['pytest.ini', 'conftest.py', 'setup.cfg']
        },
        'javascript': {
            'react': ['package.json'],
            'vue': ['vue.config.js'],
            'angular': ['angular.json'],
            'nextjs': ['next.config.js'],
            'express': ['express'],
            'nestjs': ['nest-cli.json']
        },
        'typescript': {
            'react': ['package.json'],
            'vue': ['package.json'],
            'angular': ['angular.json'],
            'nextjs': ['next.config.js'],
            'nestjs': ['nest-cli.json']
        }
    }

    # Known libraries by dependency name
    LIBRARIES = {
        'python': [
            'requests', 'flask', 'django', 'fastapi', 'sqlalchemy',
            'numpy', 'pandas', 'matplotlib', 'pillow', 'cryptography',
            'pyyaml', 'pydantic', 'celery', 'redis', 'psycopg2'
        ],
        'javascript': [
            'react', 'vue', 'angular', 'express', 'lodash', 'axios',
            'moment', 'chalk', 'dotenv', 'express', 'mongoose'
        ]
    }

    def __init__(self, project_path: str = "."):
        """
        Initialize the stack detector.

        Args:
            project_path: Path to the project directory
        """
        self.project_path = Path(project_path).resolve()
        self.stack_info: Dict[str, Any] = {}

    def detect(self) -> Dict[str, Any]:
        """
        Detect the technology stack.

        Returns:
            Dictionary with detected stack information
        """
        logger.info(f"Detecting stack at: {self.project_path}")

        self.stack_info = {
            "frameworks": self._detect_frameworks(),
            "libraries": self._detect_libraries(),
            "databases": self._detect_databases(),
            "tools": self._detect_tools(),
            "package_managers": self._detect_package_managers()
        }

        return self.stack_info

    def _detect_frameworks(self) -> List[Dict[str, str]]:
        """Detect frameworks used in the project."""
        frameworks = []

        # Check for Python frameworks
        python_frameworks = self._check_python_frameworks()
        frameworks.extend(python_frameworks)

        # Check for JavaScript/TypeScript frameworks
        js_frameworks = self._check_js_frameworks()
        frameworks.extend(js_frameworks)

        return frameworks

    def _check_python_frameworks(self) -> List[Dict[str, str]]:
        """Check for Python frameworks."""
        frameworks = []

        # Check requirements.txt
        req_file = self.project_path / "requirements.txt"
        if req_file.exists():
            content = req_file.read_text().lower()
            for fw in ['django', 'flask', 'fastapi', 'pyramid', 'tornado', 'pytest']:
                if fw in content:
                    frameworks.append({"name": fw, "language": "python"})

        # Check pyproject.toml
        pyproject = self.project_path / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text().lower()
            for fw in ['django', 'flask', 'fastapi']:
                if fw in content:
                    frameworks.append({"name": fw, "language": "python"})

        # Check for framework-specific files
        for root, dirs, files in os.walk(self.project_path):
            if 'django' in [f.lower() for f in files]:
                if not any(fw['name'] == 'django' for fw in frameworks):
                    frameworks.append({"name": "django", "language": "python"})
            if 'manage.py' in files:
                if not any(fw['name'] == 'django' for fw in frameworks):
                    frameworks.append({"name": "django", "language": "python"})
            if 'app.py' in files or 'wsgi.py' in files:
                if not any(fw['name'] in ['flask', 'fastapi'] for fw in frameworks):
                    frameworks.append({"name": "flask", "language": "python"})

        return frameworks

    def _check_js_frameworks(self) -> List[Dict[str, str]]:
        """Check for JavaScript/TypeScript frameworks."""
        frameworks = []

        package_json = self.project_path / "package.json"
        if package_json.exists():
            try:
                content = json.loads(package_json.read_text())
                deps = {**content.get('dependencies', {}), **content.get('devDependencies', {})}

                for fw in ['react', 'vue', 'angular', 'express', 'next', 'nest']:
                    if fw in deps:
                        lang = 'typescript' if content.get('typescript') or 'ts' in str(deps) else 'javascript'
                        frameworks.append({"name": fw, "language": lang})
            except Exception as e:
                logger.warning(f"Failed to parse package.json: {e}")

        return frameworks

    def _detect_libraries(self) -> List[str]:
        """Detect libraries used in the project."""
        libraries = []

        # Check requirements.txt
        req_file = self.project_path / "requirements.txt"
        if req_file.exists():
            content = req_file.read_text().lower()
            for lib in self.LIBRARIES['python']:
                if lib in content:
                    libraries.append(lib)

        # Check package.json
        package_json = self.project_path / "package.json"
        if package_json.exists():
            try:
                content = json.loads(package_json.read_text())
                deps = {**content.get('dependencies', {}), **content.get('devDependencies', {})}
                for lib in self.LIBRARIES['javascript']:
                    if lib in deps:
                        libraries.append(lib)
            except Exception:
                pass

        return list(set(libraries))

    def _detect_databases(self) -> List[str]:
        """Detect databases used in the project."""
        databases = []

        # Check for database-related files and configs
        indicators = {
            'postgresql': ['postgresql', 'postgres', 'pg_'],
            'mysql': ['mysql', 'mariadb'],
            'mongodb': ['mongodb', 'mongoose'],
            'redis': ['redis'],
            'sqlite': ['sqlite']
        }

        # Check requirements.txt
        req_file = self.project_path / "requirements.txt"
        if req_file.exists():
            content = req_file.read_text().lower()
            for db, keywords in indicators.items():
                if any(kw in content for kw in keywords):
                    databases.append(db)

        # Check package.json
        package_json = self.project_path / "package.json"
        if package_json.exists():
            try:
                content = json.loads(package_json.read_text())
                deps = str(content.get('dependencies', {})).lower()
                for db, keywords in indicators.items():
                    if any(kw in deps for kw in keywords):
                        databases.append(db)
            except Exception:
                pass

        # Check for database config files
        for db in ['postgresql.conf', 'my.cnf', 'mongod.conf']:
            if (self.project_path / db).exists():
                databases.append(db.split('.')[0])

        return list(set(databases))

    def _detect_tools(self) -> List[str]:
        """Detect development tools used."""
        tools = []

        # Check for tool config files
        tool_files = {
            'pytest': ['pytest.ini', 'setup.cfg', 'pyproject.toml'],
            'eslint': ['.eslintrc', '.eslintrc.js', '.eslintrc.json'],
            'prettier': ['.prettierrc', '.prettierrc.js', 'prettier.config.js'],
            'webpack': ['webpack.config.js'],
            'vite': ['vite.config.js'],
            'gulp': ['gulpfile.js'],
            'make': ['Makefile'],
            'docker': ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml']
        }

        for tool, files in tool_files.items():
            for f in files:
                if (self.project_path / f).exists():
                    tools.append(tool)
                    break

        return tools

    def _detect_package_managers(self) -> List[str]:
        """Detect package managers used."""
        managers = []

        # Check for lock files
        lock_files = {
            'pip': ['requirements.lock', 'Pipfile.lock'],
            'npm': ['package-lock.json'],
            'yarn': ['yarn.lock'],
            'poetry': ['poetry.lock'],
            'pipenv': ['Pipfile']
        }

        for manager, files in lock_files.items():
            for f in files:
                if (self.project_path / f).exists():
                    managers.append(manager)
                    break

        return managers

    def get_summary(self) -> str:
        """Get a human-readable summary of the detected stack."""
        if not self.stack_info:
            self.detect()

        lines = ["Detected Stack:"]

        frameworks = self.stack_info.get('frameworks', [])
        if frameworks:
            lines.append(f"  Frameworks: {', '.join(f['name'] for f in frameworks)}")

        libraries = self.stack_info.get('libraries', [])
        if libraries:
            lines.append(f"  Libraries: {', '.join(libraries[:5])}")

        databases = self.stack_info.get('databases', [])
        if databases:
            lines.append(f"  Databases: {', '.join(databases)}")

        tools = self.stack_info.get('tools', [])
        if tools:
            lines.append(f"  Tools: {', '.join(tools)}")

        return "\n".join(lines)
