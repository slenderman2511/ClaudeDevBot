"""
Init Command

Initialize DevBot in the current repository.
"""

import os
import sys
import json
from pathlib import Path

from claudebot.observability.logger import get_logger

logger = get_logger(__name__)


def run_init(args):
    """Run the init command."""
    project_path = Path(args.path).resolve()

    print("\n" + "="*50)
    print("DEVBOT INITIALIZING")
    print("="*50 + "\n")

    # Step 1: Detect repository
    print("[1/6] Detecting repository...")
    repo_info = detect_repository(project_path)
    print(f"      Repository: {repo_info.get('name', 'Unknown')}")
    print(f"      Type: {repo_info.get('type', 'Unknown')}")

    # Step 2: Ask for configuration
    print("\n[2/6] Configuring environment...")
    config = prompt_configuration()
    print("      Configuration saved")

    # Step 3: Create workspace
    print("\n[3/6] Creating DevBot workspace...")
    workspace_path = project_path / ".devbot"
    workspace_path.mkdir(exist_ok=True)

    # Save configuration
    config_file = workspace_path / "config.yaml"
    save_config(config_file, config)

    # Save state
    state = {
        "attached": True,
        "version": "1.0.0",
        "initialized_at": get_timestamp()
    }
    state_file = workspace_path / "devbot_state.json"
    state_file.write_text(json.dumps(state, indent=2))

    # Create OpenSpec directory
    openspec_path = project_path / "openspec"
    (openspec_path / "features").mkdir(parents=True, exist_ok=True)
    (openspec_path / "context").mkdir(parents=True, exist_ok=True)
    (openspec_path / "plans").mkdir(parents=True, exist_ok=True)

    print(f"      Workspace: {workspace_path}")

    # Step 4: Scan project
    print("\n[4/6] Scanning project...")
    if args.skip_scan:
        print("      Skipped (--skip-scan)")
    else:
        from claudebot.scanner.project_scanner import ProjectScanner
        from claudebot.scanner.stack_detector import StackDetector

        scanner = ProjectScanner(str(project_path))
        project_info = scanner.scan()

        detector = StackDetector(str(project_path))
        stack_info = detector.detect()

        result = {
            "project": project_info,
            "stack": stack_info
        }

        profile_file = workspace_path / "project_profile.json"
        profile_file.write_text(json.dumps(result, indent=2))

        lang = project_info.get('language', ['Unknown'])
        print(f"      Language: {lang[0] if lang else 'Unknown'}")

    # Step 5: Generate code graph
    print("\n[5/6] Generating code graph...")
    if args.skip_graph:
        print("      Skipped (--skip-graph)")
    else:
        from claudebot.graph.code_graph_builder import CodeGraphBuilder

        graph_builder = CodeGraphBuilder(str(project_path))
        graph = graph_builder.build()

        graph_file = workspace_path / "code_graph.json"
        graph_file.write_text(json.dumps(graph, indent=2))

        print(f"      Nodes: {len(graph.get('nodes', {}))}")
        print(f"      Edges: {len(graph.get('edges', []))}")

    # Step 6: Initialize OpenSpec
    print("\n[6/6] Initializing OpenSpec...")
    generate_project_context(project_path, repo_info)
    print("      OpenSpec initialized")

    print("\n" + "="*50)
    print("DEVBOT IS READY")
    print("="*50)
    print("""
Next steps:
  1. Create a feature: devbot feature <name>
  2. Plan the feature: devbot plan <name>
  3. Implement it: devbot implement <name>

For help: devbot --help
""")


def detect_repository(project_path: Path) -> dict:
    """Detect the repository type and information."""
    info = {
        "name": project_path.name,
        "type": "directory",
        "path": str(project_path)
    }

    # Check for git
    git_dir = project_path / ".git"
    if git_dir.exists():
        info["type"] = "git"

        # Try to get git remote
        import subprocess
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                info["remote"] = result.stdout.strip()
        except Exception:
            pass

    return info


def prompt_configuration() -> dict:
    """Prompt for configuration values."""
    config = {}

    # Claude API Key
    print("\nPlease provide the required configuration.")
    print("(Press Enter to skip optional fields)\n")

    # Check for existing env vars first
    claude_key = os.environ.get('CLAUDE_API_KEY', '')
    telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    github_token = os.environ.get('GITHUB_TOKEN', '')
    default_model = os.environ.get('CLAUDE_MODEL', 'claude-sonnet')

    # Claude API Key
    prompt = "Claude API Key"
    if claude_key:
        prompt += f" [{'*' * 20}...]: "
    else:
        prompt += ": "

    value = input(prompt)
    config['claude_api_key'] = value or claude_key or ''

    # Telegram Bot Token
    value = input(f"Telegram Bot Token (optional): ")
    config['telegram_token'] = value or telegram_token or ''

    # GitHub Token
    value = input(f"GitHub Token (optional): ")
    config['github_token'] = value or github_token or ''

    # Default Model
    value = input(f"Default model [{default_model}]: ")
    config['model'] = value or default_model

    return config


def save_config(config_file: Path, config: dict):
    """Save configuration to YAML file."""
    import yaml

    # Filter out empty values
    config = {k: v for k, v in config.items() if v}

    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)


def generate_project_context(project_path: Path, repo_info: dict):
    """Generate initial project context file."""
    openspec_path = project_path / "openspec" / "context"
    openspec_path.mkdir(parents=True, exist_ok=True)

    # Load project profile
    profile_file = project_path / ".devbot" / "project_profile.json"
    profile = {}
    if profile_file.exists():
        profile = json.loads(profile_file.read_text())

    # Build context content
    content = f"""# Project Context

## Overview
Project: {repo_info.get('name', 'Unknown')}

## Repository
Type: {repo_info.get('type', 'Unknown')}
Remote: {repo_info.get('remote', 'N/A')}

## Technology Stack
"""

    # Add language info
    languages = profile.get('project', {}).get('language', [])
    if languages:
        content += f"- Language: {', '.join(languages)}\n"

    # Add framework info
    frameworks = profile.get('stack', {}).get('frameworks', [])
    if frameworks:
        content += "- Framework: " + ", ".join([f['name'] for f in frameworks]) + "\n"

    # Add tools
    tools = profile.get('stack', {}).get('tools', [])
    if tools:
        content += "- Tools: " + ", ".join(tools) + "\n"

    content += """
## Architecture Notes

<!-- Add your project architecture notes here -->

## Key Components

<!-- List key components and their purposes -->

## Dependencies

<!-- List main dependencies and their roles -->
"""

    context_file = openspec_path / "project.md"
    context_file.write_text(content)


def get_timestamp() -> str:
    """Get current timestamp."""
    from datetime import datetime
    return datetime.now().isoformat()
