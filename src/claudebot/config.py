# .claudebot/config.py
"""Configuration loading and management"""

import os
import yaml
import configparser
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from functools import lru_cache


@dataclass
class ServerConfig:
    """Server configuration"""
    host: str = "localhost"
    port: int = 8765
    port_auto_increment: bool = True
    api_key: Optional[str] = None
    rate_limit: int = 60  # requests per minute


@dataclass
class AgentsConfig:
    """Agents configuration"""
    enabled: list[str] = field(default_factory=lambda: ["spec", "code"])
    timeout: int = 300  # seconds


@dataclass
class ClaudeConfig:
    """Claude API configuration"""
    model: str = "claude-3-5-sonnet-20241022"
    api_key: Optional[str] = None


@dataclass
class GitConfig:
    """Git configuration"""
    auto_commit: bool = False
    default_branch: str = "main"


@dataclass
class Config:
    """Main configuration"""
    server: ServerConfig = field(default_factory=ServerConfig)
    agents: AgentsConfig = field(default_factory=AgentsConfig)
    claude: ClaudeConfig = field(default_factory=ClaudeConfig)
    git: GitConfig = field(default_factory=GitConfig)

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        """Create Config from dictionary"""
        return cls(
            server=ServerConfig(**data.get("server", {})),
            agents=AgentsConfig(**data.get("agents", {})),
            claude=ClaudeConfig(**data.get("claude", {})),
            git=GitConfig(**data.get("git", {}))
        )


@lru_cache()
def get_config_path() -> Path:
    """Get config file path - checks multiple locations"""
    # Priority: current dir .claudebot > parent .claudebot > package default
    locations = [
        Path(".claudebot/config.yaml"),
        Path(__file__).parent / "config.yaml",
    ]

    for path in locations:
        if path.exists():
            return path

    # Default to package config
    return Path(__file__).parent / "config.yaml"


def get_rc_path() -> Optional[Path]:
    """Get .claudebotrc file path"""
    # Check in current directory and parent
    locations = [
        Path(".claudebotrc"),
        Path(".claudebot/.claudebotrc"),
    ]

    for path in locations:
        if path.exists():
            return path

    return None


def load_rc_config() -> dict:
    """Load .claudebotrc quick config file (INI format)"""
    rc_path = get_rc_path()
    if not rc_path:
        return {}

    parser = configparser.ConfigParser()
    parser.read(rc_path)

    config = {}
    for section in parser.sections():
        for key, value in parser.items(section):
            # Convert types
            if key in ["port", "rate_limit", "timeout"]:
                config[key] = int(value)
            elif key in ["port_auto_increment", "auto_commit"]:
                config[key] = value.lower() in ("true", "1", "yes")
            else:
                config[key] = value

    return config


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from YAML file and .claudebotrc"""
    if config_path is None:
        config_path = get_config_path()

    if not config_path.exists():
        return Config()

    with open(config_path, 'r') as f:
        data = yaml.safe_load(f) or {}

    # Apply environment variable overrides
    config = Config.from_dict(data)

    # Override with .claudebotrc (INI format)
    rc_config = load_rc_config()
    for key, value in rc_config.items():
        if hasattr(config.server, key):
            setattr(config.server, key, value)
        elif hasattr(config.agents, key):
            setattr(config.agents, key, value)
        elif hasattr(config.claude, key):
            setattr(config.claude, key, value)
        elif hasattr(config.git, key):
            setattr(config.git, key, value)

    # Override with environment variables (highest priority)
    if api_key := os.environ.get("CLAUDE_API_KEY"):
        config.claude.api_key = api_key

    if api_key := os.environ.get("CLAUDEBOT_API_KEY"):
        config.server.api_key = api_key

    if port := os.environ.get("CLAUDEBOT_PORT"):
        config.server.port = int(port)

    # Seed TELEGRAM_BOT_TOKEN from config.yaml into env if not already set
    if "TELEGRAM_BOT_TOKEN" not in os.environ:
        if telegram_token := data.get("telegram_token"):
            os.environ["TELEGRAM_BOT_TOKEN"] = telegram_token

    return config


def reload_config() -> Config:
    """Reload config (clears cache and reloads)"""
    get_config_path.cache_clear()
    return load_config()
