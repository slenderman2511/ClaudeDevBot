"""
Git Tools Module

Wrapper for Git operations.
"""

import subprocess
from typing import Any, Dict, Optional, List

from claudebot.tools.tool import Tool, ToolResult
from claudebot.observability.logger import get_logger

logger = get_logger(__name__)


class GitTool(Tool):
    """
    Tool for executing Git operations.

    Provides capabilities for git status, commit, push, pull, and branch operations.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            name="git",
            description="Execute Git operations for version control",
            config=config or {}
        )
        self.default_branch = self.config.get('default_branch', 'main')
        self.commit_prefix = self.config.get('commit_message_prefix', '[ClaudeBot]')
        self.repo_path = self.config.get('repo_path', '.')

    def _run_git(self, args: List[str], cwd: Optional[str] = None) -> subprocess.CompletedProcess:
        """Run a git command."""
        cwd = cwd or self.repo_path
        cmd = ['git'] + args
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
        return result

    def execute(self, command: str, **kwargs) -> ToolResult:
        """Execute a Git command."""
        try:
            cmd = [command]
            if kwargs:
                for key, value in kwargs.items():
                    if isinstance(value, bool):
                        if value:
                            cmd.append(f'--{key}')
                    else:
                        cmd.extend([f'--{key}', str(value)])

            result = self._run_git(cmd)
            if result.returncode == 0:
                return ToolResult(
                    success=True,
                    output={'command': command, 'output': result.stdout},
                    metadata={'command': command, 'returncode': result.returncode}
                )
            else:
                return ToolResult(success=False, output=None, error=result.stderr)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def status(self, repo_path: Optional[str] = None) -> ToolResult:
        """Get git status."""
        try:
            result = self._run_git(['status', '--porcelain'], cwd=repo_path)
            if result.returncode == 0:
                return ToolResult(
                    success=True,
                    output={'status': 'clean' if not result.stdout.strip() else 'dirty', 'details': result.stdout},
                    metadata={'repo_path': repo_path or self.repo_path}
                )
            return ToolResult(success=False, output=None, error=result.stderr)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def add(self, files: List[str], repo_path: Optional[str] = None) -> ToolResult:
        """Stage files for commit."""
        try:
            result = self._run_git(['add'] + files, cwd=repo_path)
            if result.returncode == 0:
                return ToolResult(success=True, output={'staged': files}, metadata={'files': files})
            return ToolResult(success=False, output=None, error=result.stderr)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def commit(self, message: str, repo_path: Optional[str] = None) -> ToolResult:
        """Commit staged changes."""
        try:
            full_message = f"{self.commit_prefix} {message}"
            result = self._run_git(['commit', '-m', full_message], cwd=repo_path)
            if result.returncode == 0:
                return ToolResult(success=True, output={'committed': True, 'message': full_message}, metadata={'message': full_message})
            return ToolResult(success=False, output=None, error=result.stderr)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def push(self, remote: str = 'origin', branch: Optional[str] = None, repo_path: Optional[str] = None) -> ToolResult:
        """Push to remote."""
        try:
            cmd = ['push', remote]
            if branch:
                cmd.append(branch)
            result = self._run_git(cmd, cwd=repo_path)
            if result.returncode == 0:
                return ToolResult(success=True, output={'pushed': True, 'remote': remote, 'branch': branch}, metadata={'remote': remote, 'branch': branch})
            return ToolResult(success=False, output=None, error=result.stderr)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def pull(self, remote: str = 'origin', branch: Optional[str] = None, repo_path: Optional[str] = None) -> ToolResult:
        """Pull from remote."""
        try:
            cmd = ['pull', remote]
            if branch:
                cmd.append(branch)
            result = self._run_git(cmd, cwd=repo_path)
            if result.returncode == 0:
                return ToolResult(success=True, output={'pulled': True, 'remote': remote, 'branch': branch}, metadata={'remote': remote, 'branch': branch})
            return ToolResult(success=False, output=None, error=result.stderr)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def branch(self, list_branches: bool = True, repo_path: Optional[str] = None) -> ToolResult:
        """List branches."""
        try:
            cmd = ['branch', '-a'] if list_branches else ['branch']
            result = self._run_git(cmd, cwd=repo_path)
            if result.returncode == 0:
                branches = [b.strip() for b in result.stdout.split('\n') if b.strip()]
                return ToolResult(success=True, output={'branches': branches}, metadata={'count': len(branches)})
            return ToolResult(success=False, output=None, error=result.stderr)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def create_branch(self, branch_name: str, repo_path: Optional[str] = None) -> ToolResult:
        """Create a new branch."""
        try:
            result = self._run_git(['checkout', '-b', branch_name], cwd=repo_path)
            if result.returncode == 0:
                return ToolResult(success=True, output={'created': True, 'branch': branch_name}, metadata={'branch': branch_name})
            return ToolResult(success=False, output=None, error=result.stderr)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def checkout(self, branch_name: str, repo_path: Optional[str] = None) -> ToolResult:
        """Checkout a branch."""
        try:
            result = self._run_git(['checkout', branch_name], cwd=repo_path)
            if result.returncode == 0:
                return ToolResult(success=True, output={'checked_out': True, 'branch': branch_name}, metadata={'branch': branch_name})
            return ToolResult(success=False, output=None, error=result.stderr)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def log(self, max_count: int = 10, repo_path: Optional[str] = None) -> ToolResult:
        """Get commit history."""
        try:
            result = self._run_git(['log', f'--max-count={max_count}', '--oneline'], cwd=repo_path)
            if result.returncode == 0:
                commits = [c.strip() for c in result.stdout.split('\n') if c.strip()]
                return ToolResult(success=True, output={'commits': commits}, metadata={'count': len(commits)})
            return ToolResult(success=False, output=None, error=result.stderr)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def diff(self, staged: bool = False, repo_path: Optional[str] = None) -> ToolResult:
        """Get diff of changes."""
        try:
            cmd = ['diff', '--staged'] if staged else ['diff']
            result = self._run_git(cmd, cwd=repo_path)
            if result.returncode == 0:
                return ToolResult(success=True, output={'diff': result.stdout}, metadata={'staged': staged})
            return ToolResult(success=False, output=None, error=result.stderr)
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def validate(self) -> bool:
        """Check if git is available."""
        try:
            result = subprocess.run(['git', '--version'], capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False


def create_git_tool(config: Optional[Dict[str, Any]] = None) -> GitTool:
    """Factory function to create Git tool."""
    return GitTool(config)
