"""
Symbol Parser Module

Parses source code to extract symbols (classes, functions, variables).
"""

import ast
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from devbot.observability.logger import get_logger

logger = get_logger(__name__)


class SymbolParser:
    """
    Parses source code to extract symbols.

    Extracts:
    - Classes with methods
    - Functions with parameters
    - Import statements
    - Variable assignments
    """

    def __init__(self, project_path: str = "."):
        """
        Initialize the symbol parser.

        Args:
            project_path: Path to the project directory
        """
        self.project_path = Path(project_path).resolve()
        self.symbols: Dict[str, List[Dict[str, Any]]] = {
            "classes": [],
            "functions": [],
            "imports": [],
            "variables": []
        }

    def parse_file(self, file_path: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse a single file to extract symbols.

        Args:
            file_path: Path to the file to parse

        Returns:
            Dictionary of extracted symbols
        """
        file_path = Path(file_path)
        symbols = {
            "classes": [],
            "functions": [],
            "imports": [],
            "variables": []
        }

        try:
            if file_path.suffix == '.py':
                symbols = self._parse_python(file_path)
            elif file_path.suffix in {'.js', '.ts', '.jsx', '.tsx'}:
                symbols = self._parse_javascript(file_path)
        except Exception as e:
            logger.warning(f"Failed to parse {file_path}: {e}")

        return symbols

    def _parse_python(self, file_path: Path) -> Dict[str, List[Dict[str, Any]]]:
        """Parse a Python file."""
        symbols = {
            "classes": [],
            "functions": [],
            "imports": [],
            "variables": []
        }

        try:
            content = file_path.read_text()
            tree = ast.parse(content)

            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        symbols["imports"].append({
                            "name": alias.name,
                            "alias": alias.asname,
                            "line": node.lineno
                        })
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        symbols["imports"].append({
                            "name": f"{module}.{alias.name}" if module else alias.name,
                            "alias": alias.asname,
                            "line": node.lineno
                        })

            # Extract classes and functions
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef):
                    class_info = {
                        "name": node.name,
                        "line": node.lineno,
                        "docstring": ast.get_docstring(node),
                        "methods": [
                            n.name for n in node.body
                            if isinstance(n, ast.FunctionDef)
                        ],
                        "bases": [self._get_name(base) for base in node.bases]
                    }
                    symbols["classes"].append(class_info)

                elif isinstance(node, ast.FunctionDef):
                    func_info = {
                        "name": node.name,
                        "line": node.lineno,
                        "docstring": ast.get_docstring(node),
                        "args": [arg.arg for arg in node.args.args],
                        "returns": self._get_name(node.returns) if node.returns else None,
                        " decorators": [self._get_name(d) for d in node.decorator_list]
                    }
                    symbols["functions"].append(func_info)

        except Exception as e:
            logger.warning(f"Failed to parse Python file {file_path}: {e}")

        return symbols

    def _parse_javascript(self, file_path: Path) -> Dict[str, List[Dict[str, Any]]]:
        """Parse a JavaScript/TypeScript file."""
        symbols = {
            "classes": [],
            "functions": [],
            "imports": [],
            "variables": []
        }

        try:
            content = file_path.read_text()

            # Extract imports
            import_pattern = r"import\s+(?:{[^}]+}|\w+)\s+from\s+['\"]([^'\"]+)['\"]"
            for match in re.finditer(import_pattern, content):
                symbols["imports"].append({
                    "name": match.group(1),
                    "line": content[:match.start()].count('\n') + 1
                })

            # Extract class declarations
            class_pattern = r"class\s+(\w+)(?:\s+extends\s+(\w+))?"
            for match in re.finditer(class_pattern, content):
                symbols["classes"].append({
                    "name": match.group(1),
                    "extends": match.group(2),
                    "line": content[:match.start()].count('\n') + 1
                })

            # Extract function declarations
            func_patterns = [
                r"function\s+(\w+)\s*\(([^)]*)\)",  # function foo()
                r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>",  # const foo = () =>
                r"(?:const|let|var)\s+(\w+)\s*=\s*function\s*\(([^)]*)\)"  # const foo = function()
            ]

            for pattern in func_patterns:
                for match in re.finditer(pattern, content):
                    args = match.group(2) if match.lastindex >= 2 else ""
                    symbols["functions"].append({
                        "name": match.group(1),
                        "args": [a.strip() for a in args.split(',') if a.strip()],
                        "line": content[:match.start()].count('\n') + 1
                    })

            # Extract variable declarations
            var_pattern = r"(?:const|let|var)\s+(\w+)\s*="
            for match in re.finditer(var_pattern, content):
                symbols["variables"].append({
                    "name": match.group(1),
                    "line": content[:match.start()].count('\n') + 1
                })

        except Exception as e:
            logger.warning(f"Failed to parse JS file {file_path}: {e}")

        return symbols

    def _get_name(self, node) -> Optional[str]:
        """Get the name from an AST node."""
        if node is None:
            return None

        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        elif isinstance(node, ast.Constant):
            return str(node.value)
        return None

    def get_all_symbols(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all symbols from all source files in the project.

        Returns:
            Dictionary of all symbols
        """
        all_symbols = {
            "classes": [],
            "functions": [],
            "imports": [],
            "variables": []
        }

        for file_path in self.project_path.rglob("*.py"):
            if not any(p in file_path.parts for p in ['venv', '__pycache__', '.venv']):
                symbols = self.parse_file(file_path)
                for key in all_symbols:
                    all_symbols[key].extend(symbols[key])

        return all_symbols
