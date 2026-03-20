"""
Code Graph Builder Module

Builds a code knowledge graph from the project source files.
"""

import os
import json
import ast
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from datetime import datetime

from claudebot.observability.logger import get_logger

logger = get_logger(__name__)


class CodeGraphBuilder:
    """
    Builds a code knowledge graph from project source files.

    Creates nodes for:
    - Files
    - Classes
    - Functions
    - APIs

    Creates edges for:
    - Imports
    - Calls
    - Dependencies
    """

    def __init__(self, project_path: str = "."):
        """
        Initialize the code graph builder.

        Args:
            project_path: Path to the project directory
        """
        self.project_path = Path(project_path).resolve()
        self.graph: Dict[str, Any] = {
            "nodes": {},
            "edges": [],
            "metadata": {}
        }

    def build(self) -> Dict[str, Any]:
        """
        Build the code graph.

        Returns:
            The code graph dictionary
        """
        logger.info(f"Building code graph for: {self.project_path}")

        self.graph = {
            "nodes": {},
            "edges": [],
            "metadata": {
                "project_path": str(self.project_path),
                "created_at": datetime.now().isoformat()
            }
        }

        # Walk through source files
        source_files = self._find_source_files()
        logger.info(f"Found {len(source_files)} source files")

        for file_path in source_files:
            self._analyze_file(file_path)

        logger.info(f"Code graph built: {len(self.graph['nodes'])} nodes, {len(self.graph['edges'])} edges")
        return self.graph

    def _find_source_files(self) -> List[Path]:
        """Find source files to analyze."""
        source_files = []
        extensions = {'.py', '.js', '.ts', '.jsx', '.tsx'}

        for root, dirs, files in os.walk(self.project_path):
            # Skip hidden and build directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', '__pycache__', 'build', 'dist']]

            for file in files:
                if Path(file).suffix in extensions:
                    source_files.append(Path(root) / file)

        return source_files

    def _analyze_file(self, file_path: Path):
        """Analyze a single source file."""
        rel_path = str(file_path.relative_to(self.project_path))

        # Add file node
        file_node = {
            "type": "file",
            "path": rel_path,
            "name": file_path.name,
            "language": self._get_language(file_path),
            "line_count": self._count_lines(file_path)
        }
        self._add_node(f"file:{rel_path}", file_node)

        # Analyze based on language
        if file_path.suffix == '.py':
            self._analyze_python_file(file_path, rel_path)
        elif file_path.suffix in {'.js', '.ts', '.jsx', '.tsx'}:
            self._analyze_js_file(file_path, rel_path)

    def _analyze_python_file(self, file_path: Path, rel_path: str):
        """Analyze a Python source file."""
        try:
            content = file_path.read_text()
            tree = ast.parse(content)

            # Find imports
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)

            # Add import edges
            for imp in imports:
                self._add_edge(f"file:{rel_path}", f"import:{imp}", "imports")

            # Find classes and functions
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef):
                    class_node = {
                        "type": "class",
                        "name": node.name,
                        "file": rel_path,
                        "line": node.lineno,
                        "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    }
                    self._add_node(f"class:{rel_path}:{node.name}", class_node)
                    self._add_edge(f"file:{rel_path}", f"class:{rel_path}:{node.name}", "contains")

                elif isinstance(node, ast.FunctionDef):
                    func_node = {
                        "type": "function",
                        "name": node.name,
                        "file": rel_path,
                        "line": node.lineno,
                        "args": [arg.arg for arg in node.args.args]
                    }
                    self._add_node(f"func:{rel_path}:{node.name}", func_node)
                    self._add_edge(f"file:{rel_path}", f"func:{rel_path}:{node.name}", "contains")

        except Exception as e:
            logger.warning(f"Failed to analyze {file_path}: {e}")

    def _analyze_js_file(self, file_path: Path, rel_path: str):
        """Analyze a JavaScript/TypeScript source file."""
        try:
            content = file_path.read_text()

            # Simple regex-based analysis for imports
            import re

            # ES6 imports: import x from 'y'
            import_pattern = r"import\s+(?:{[^}]+}|\w+)\s+from\s+['\"]([^'\"]+)['\"]"
            imports = re.findall(import_pattern, content)

            for imp in imports:
                self._add_edge(f"file:{rel_path}", f"import:{imp}", "imports")

            # Find function declarations
            func_pattern = r"(?:function|const|let|var)\s+(\w+)\s*="
            functions = re.findall(func_pattern, content)
            for func_name in functions:
                func_node = {
                    "type": "function",
                    "name": func_name,
                    "file": rel_path
                }
                self._add_node(f"func:{rel_path}:{func_name}", func_node)
                self._add_edge(f"file:{rel_path}", f"func:{rel_path}:{func_name}", "contains")

            # Find class declarations
            class_pattern = r"class\s+(\w+)"
            classes = re.findall(class_pattern, content)
            for class_name in classes:
                class_node = {
                    "type": "class",
                    "name": class_name,
                    "file": rel_path
                }
                self._add_node(f"class:{rel_path}:{class_name}", class_node)
                self._add_edge(f"file:{rel_path}", f"class:{rel_path}:{class_name}", "contains")

        except Exception as e:
            logger.warning(f"Failed to analyze {file_path}: {e}")

    def _add_node(self, node_id: str, data: Dict[str, Any]):
        """Add a node to the graph."""
        self.graph["nodes"][node_id] = data

    def _add_edge(self, source: str, target: str, edge_type: str):
        """Add an edge to the graph."""
        self.graph["edges"].append({
            "source": source,
            "target": target,
            "type": edge_type
        })

    def _get_language(self, file_path: Path) -> str:
        """Get the language for a file."""
        ext = file_path.suffix.lower()
        lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'react',
            '.tsx': 'react'
        }
        return lang_map.get(ext, 'unknown')

    def _count_lines(self, file_path: Path) -> int:
        """Count lines in a file."""
        try:
            return len(file_path.read_text().splitlines())
        except Exception:
            return 0

    def save_graph(self, output_path: Optional[str] = None) -> str:
        """
        Save the graph to a file.

        Args:
            output_path: Path to save the graph (default: .devbot/code_graph.json)

        Returns:
            Path to saved file
        """
        if output_path is None:
            devbot_dir = self.project_path / ".devbot"
            devbot_dir.mkdir(exist_ok=True)
            output_path = devbot_dir / "code_graph.json"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(self.graph, f, indent=2)

        logger.info(f"Code graph saved to: {output_path}")
        return str(output_path)

    def get_summary(self) -> str:
        """Get a summary of the code graph."""
        node_types = {}
        for node_id, node_data in self.graph.get("nodes", {}).items():
            node_type = node_data.get("type", "unknown")
            node_types[node_type] = node_types.get(node_type, 0) + 1

        lines = ["Code Graph Summary:"]
        lines.append(f"  Total nodes: {len(self.graph.get('nodes', {}))}")
        lines.append(f"  Total edges: {len(self.graph.get('edges', []))}")
        lines.append("  Node types:")
        for node_type, count in node_types.items():
            lines.append(f"    - {node_type}: {count}")

        return "\n".join(lines)
