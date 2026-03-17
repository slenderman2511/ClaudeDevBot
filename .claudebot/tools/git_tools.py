# .claudebot/tools/git_tools.py
"""Git operations wrapper"""

import subprocess
import os
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

class GitTools:
    """Wrapper for git operations"""

    def __init__(self, repo_path: str):
        self.repo_path = repo_path

    def _run(self, *args) -> str:
        """Run git command"""
        result = subprocess.run(
            ["git", *args],
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"Git error: {result.stderr}")
        return result.stdout

    async def status(self) -> str:
        """Get git status"""
        return self._run("status", "--porcelain")

    async def branch(self) -> str:
        """Get current branch"""
        return self._run("branch", "--show-current")

    async def branches(self) -> List[str]:
        """List all branches"""
        output = self._run("branch", "-a")
        return [b.strip() for b in output.split('\n') if b]

    async def checkout(self, branch: str) -> str:
        """Checkout to branch"""
        return self._run("checkout", branch)

    async def pull(self) -> str:
        """Pull from remote"""
        return self._run("pull")

    async def commit(self, message: str) -> str:
        """Commit changes"""
        self._run("add", "-A")
        return self._run("commit", "-m", message)

    async def log(self, n: int = 10) -> List[dict]:
        """Get commit history"""
        output = self._run("log", f"-{n}", "--oneline", "--pretty=format:%H|%s|%an|%ar")
        commits = []
        for line in output.split('\n'):
            if '|' in line:
                parts = line.split('|')
                commits.append({
                    "hash": parts[0],
                    "message": parts[1],
                    "author": parts[2],
                    "date": parts[3]
                })
        return commits
