# src/tests/conftest.py
"""Pytest fixtures and configuration."""

import os
import sys
import tempfile
import pytest

# Ensure claudebot is importable from src/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def temp_repo(tmp_path):
    """A temporary directory simulating a git repo."""
    repo = tmp_path / "test_repo"
    repo.mkdir()
    # Create a minimal git directory so scanner/graph tools don't crash
    (repo / ".git").mkdir()
    return repo


@pytest.fixture
def agent_context(temp_repo):
    """A minimal AgentContext for testing."""
    from claudebot.agents.base_agent import AgentContext
    return AgentContext(
        repo_path=str(temp_repo),
        branch="main",
        claude_api_key="test-key",
        config={},
    )


@pytest.fixture
def mock_api_key(monkeypatch):
    """Set fake API keys in environment."""
    monkeypatch.setenv("CLAUDE_API_KEY", "test-claude-api-key")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-telegram-token")
