"""
Config Command

Manage DevBot configuration.
"""

import os
import sys
import json
import yaml
from pathlib import Path

from claudebot.observability.logger import get_logger

logger = get_logger(__name__)


def run_config(args):
    """Run the config command."""
    project_path = Path(args.path).resolve()
    config_file = project_path / ".devbot" / "config.yaml"

    # Load existing config
    config = {}
    if config_file.exists():
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f) or {}

    # Handle --list
    if args.list:
        print("\n" + "="*50)
        print("DEVBOT CONFIGURATION")
        print("="*50 + "\n")

        if config:
            for key, value in config.items():
                # Mask sensitive values
                if key in ['claude_api_key', 'telegram_token', 'github_token']:
                    if value:
                        value = '*' * 20
                print(f"  {key}: {value}")
        else:
            print("  No configuration found. Run 'devbot init' to configure.")

        print("\n" + "="*50 + "\n")
        return

    # Handle --get
    if args.get:
        value = config.get(args.get)
        if value:
            # Mask sensitive values
            if args.get in ['claude_api_key', 'telegram_token', 'github_token']:
                value = '*' * 20
            print(value)
        else:
            print(f"Configuration '{args.get}' not found.")
        return

    # Handle --set
    if args.set:
        key, value = args.set
        config[key] = value

        # Save config
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)

        print(f"Configuration '{key}' set to: {value}")
        return

    # No arguments - interactive mode
    interactive_config(config, project_path)


def interactive_config(config: dict, project_path: Path):
    """Interactive configuration management."""
    config_file = project_path / ".devbot" / "config.yaml"

    print("\n" + "="*50)
    print("DEVBOT CONFIGURATION")
    print("="*50 + "\n")

    print("Current configuration:")
    for key, value in config.items():
        if key in ['claude_api_key', 'telegram_token', 'github_token']:
            if value:
                value = '*' * 20
        print(f"  {key}: {value}")

    print("\n" + "-"*50)
    print("Update configuration (press Enter to keep current value):")
    print("-"*50 + "\n")

    # Claude API Key
    current = config.get('claude_api_key', '')
    prompt = "Claude API Key"
    if current:
        prompt += f" [{'*' * 20}]"
    value = input(f"{prompt}: ")
    if value:
        config['claude_api_key'] = value

    # Telegram Token
    current = config.get('telegram_token', '')
    value = input(f"Telegram Token [{'*' * 20 if current else ''}]: ")
    if value:
        config['telegram_token'] = value

    # GitHub Token
    current = config.get('github_token', '')
    value = input(f"GitHub Token [{'*' * 20 if current else ''}]: ")
    if value:
        config['github_token'] = value

    # Model
    current = config.get('model', 'claude-sonnet')
    value = input(f"Default model [{current}]: ")
    if value:
        config['model'] = value

    # Save config
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

    print("\nConfiguration saved.\n")


def load_config(project_path: str = ".") -> dict:
    """Load configuration from file and environment variables."""
    project_path = Path(project_path).resolve()
    config_file = project_path / ".devbot" / "config.yaml"

    config = {}

    # Load from file
    if config_file.exists():
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f) or {}

    # Override with environment variables
    env_vars = {
        'claude_api_key': 'CLAUDE_API_KEY',
        'telegram_token': 'TELEGRAM_BOT_TOKEN',
        'github_token': 'GITHUB_TOKEN',
        'model': 'CLAUDE_MODEL',
    }

    for config_key, env_var in env_vars.items():
        env_value = os.environ.get(env_var)
        if env_value:
            config[config_key] = env_value

    return config
