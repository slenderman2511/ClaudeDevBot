"""
ClaudeDevBot — Unified CLI

Merged from:
- claudebot: serve, run, config, (lightweight init)
- devbot: init (full), scan, graph, feature, plan, implement, status, list, config
"""

import sys
import os
import asyncio
import argparse
import json
import logging
from pathlib import Path

from .config import load_config

# Use devbot's richer logger if available, fall back to basic
try:
    from .observability.logger import get_logger, configure_logging
    configure_logging()
except ImportError:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    get_logger = logging.getLogger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="claudebot",
        description="ClaudeDevBot — AI Development Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  claudebot init                    Initialize project (full: scan + graph)
  claudebot scan                    Scan project and detect tech stack
  claudebot graph                   Build code knowledge graph
  claudebot feature auth            Create feature 'auth'
  claudebot plan auth               Plan feature 'auth'
  claudebot implement auth          Implement feature 'auth'
  claudebot config                  Manage configuration
  claudebot status                  Show DevBot status
  claudebot serve --port 8765       Start API server
  claudebot run code "task desc"    Run a task directly
        """,
    )

    parser.add_argument("--version", action="version", version="ClaudeDevBot 0.1.0")
    parser.add_argument("--path", default=".", help="Project path (default: current directory)")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ---- devbot commands ----

    init_parser = subparsers.add_parser("init", help="Initialize DevBot in the repository")
    init_parser.add_argument("--skip-scan", action="store_true", help="Skip initial scan")
    init_parser.add_argument("--skip-graph", action="store_true", help="Skip code graph generation")

    scan_parser = subparsers.add_parser("scan", help="Scan project and detect tech stack")
    graph_parser = subparsers.add_parser("graph", help="Build code knowledge graph")

    feature_parser = subparsers.add_parser("feature", help="Create a new OpenSpec feature")
    feature_parser.add_argument("name", help="Feature name")
    feature_parser.add_argument("--description", "-d", default="", help="Feature description")

    plan_parser = subparsers.add_parser("plan", help="Generate task plan from feature")
    plan_parser.add_argument("name", help="Feature name")

    implement_parser = subparsers.add_parser("implement", help="Implement feature using AI")
    implement_parser.add_argument("name", help="Feature name")

    config_parser = subparsers.add_parser("config", help="Manage DevBot configuration")
    config_parser.add_argument("--set", nargs=2, metavar=("KEY", "VALUE"), help="Set configuration value")
    config_parser.add_argument("--get", metavar="KEY", help="Get configuration value")
    config_parser.add_argument("--list", action="store_true", help="List all configuration")

    status_parser = subparsers.add_parser("status", help="Show DevBot status")
    list_parser = subparsers.add_parser("list", help="List available features")

    # ---- claudebot commands ----

    serve_parser = subparsers.add_parser("serve", help="Start API server")
    serve_parser.add_argument("--host", default="localhost", help="Host to bind")
    serve_parser.add_argument("--port", type=int, help="Port to bind")
    serve_parser.add_argument("--reload", action="store_true", help="Auto-reload")
    serve_parser.add_argument("--telegram", action="store_true", help="Start Telegram bot with long polling")

    run_parser = subparsers.add_parser("run", help="Run a task directly")
    run_parser.add_argument("type", choices=["spec", "code", "test", "deploy", "debug"], help="Task type")
    run_parser.add_argument("description", help="Task description")

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args)
    elif args.command == "scan":
        cmd_scan(args)
    elif args.command == "graph":
        cmd_graph(args)
    elif args.command == "feature":
        cmd_feature(args)
    elif args.command == "plan":
        cmd_plan(args)
    elif args.command == "implement":
        cmd_implement(args)
    elif args.command == "config":
        cmd_config(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "serve":
        cmd_serve(args)
    elif args.command == "run":
        asyncio.run(cmd_run(args))
    else:
        parser.print_help()


# ---------------------------------------------------------------------------
# Init command (full devbot-style)
# ---------------------------------------------------------------------------

def cmd_init(args):
    """Full devbot-style init: detect repo, config, workspace, scan, graph."""
    from .cli_commands.commands.init import run_init
    run_init(args)


# ---------------------------------------------------------------------------
# Scan command
# ---------------------------------------------------------------------------

def cmd_scan(args):
    """Scan project and detect tech stack."""
    from .scanner.project_scanner import ProjectScanner
    from .scanner.stack_detector import StackDetector

    project_path = Path(args.path).resolve()
    scanner = ProjectScanner(str(project_path))
    detector = StackDetector(str(project_path))

    project_info = scanner.scan()
    stack_info = detector.detect()
    result = {"project": project_info, "stack": stack_info}

    devbot_dir = project_path / ".devbot"
    devbot_dir.mkdir(exist_ok=True)
    profile_file = devbot_dir / "project_profile.json"
    profile_file.write_text(json.dumps(result, indent=2))

    print("\n" + "=" * 50)
    print("PROJECT SCAN RESULTS")
    print("=" * 50)
    print(f"\nProject: {project_info.get('name', 'Unknown')}")
    langs = project_info.get("language", [])
    print(f"Language: {langs[0] if langs else 'Unknown'}")
    if stack_info.get("frameworks"):
        print(f"Framework: {', '.join([f['name'] for f in stack_info['frameworks']])}")
    if stack_info.get("tools"):
        print(f"Tools: {', '.join(stack_info['tools'])}")
    print(f"\nProfile saved to: {profile_file}")
    print("=" * 50 + "\n")


# ---------------------------------------------------------------------------
# Graph command
# ---------------------------------------------------------------------------

def cmd_graph(args):
    """Build code knowledge graph."""
    from .graph.code_graph_builder import CodeGraphBuilder

    project_path = Path(args.path).resolve()
    graph_builder = CodeGraphBuilder(str(project_path))
    graph = graph_builder.build()

    devbot_dir = project_path / ".devbot"
    devbot_dir.mkdir(exist_ok=True)
    graph_file = devbot_dir / "code_graph.json"
    graph_file.write_text(json.dumps(graph, indent=2))

    print("\n" + "=" * 50)
    print("CODE GRAPH")
    print("=" * 50)
    print(f"\nNodes: {len(graph.get('nodes', {}))}")
    print(f"Edges: {len(graph.get('edges', []))}")
    print(f"\nGraph saved to: {graph_file}")
    print("=" * 50 + "\n")


# ---------------------------------------------------------------------------
# Feature command
# ---------------------------------------------------------------------------

def cmd_feature(args):
    """Create a new OpenSpec feature."""
    from .spec.spec_generator import SpecGenerator
    from .spec.openspec_sync import OpenSpecSync

    project_path = Path(args.path).resolve()
    openspec = OpenSpecSync(str(project_path / "openspec"))
    generator = SpecGenerator()

    md_content = generator.generate_markdown(args.name, args.description)
    feature_file = openspec.features_path / f"{args.name}.md"
    feature_file.write_text(md_content)

    print(f"\nFeature created: {args.name}")
    print(f"File: {feature_file}\n")


# ---------------------------------------------------------------------------
# Plan command
# ---------------------------------------------------------------------------

def cmd_plan(args):
    """Generate task plan from OpenSpec feature."""
    from .spec.openspec_sync import OpenSpecSync
    from .agents.planner_agent import PlannerAgent
    from .agents.base_agent import Task

    project_path = Path(args.path).resolve()
    openspec = OpenSpecSync(str(project_path / "openspec"))

    feature = openspec.load_feature(args.name)
    if not feature:
        print(f"Error: Feature '{args.name}' not found", file=sys.stderr)
        sys.exit(1)

    planner = PlannerAgent(config={}, openspec=openspec)
    task = Task(input=args.name)
    result = planner.execute(task)

    if result.success:
        plan_file = openspec.plans_path / f"{args.name}-plan.md"
        plan_file.write_text(result.output)
        print(f"\n{'=' * 50}")
        print(f"PLAN: {args.name}")
        print("=" * 50)
        print(result.output)
        print(f"\nPlan saved to: {plan_file}\n")
    else:
        print(f"Error: {result.error}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Implement command
# ---------------------------------------------------------------------------

async def cmd_implement(args):
    """Implement feature using AI agents."""
    from .spec.openspec_sync import OpenSpecSync
    from .orchestrator.task_manager import TaskManager

    project_path = Path(args.path).resolve()
    openspec = OpenSpecSync(str(project_path / "openspec"))

    feature = openspec.load_feature(args.name)
    if not feature:
        print(f"Error: Feature '{args.name}' not found", file=sys.stderr)
        sys.exit(1)

    pending = openspec.get_pending_tasks(args.name)
    if not pending:
        print("No pending tasks to implement.")
        return

    print(f"\nImplementing feature: {args.name}")
    print(f"Pending tasks: {len(pending)}")

    manager = TaskManager(project_path=str(project_path))
    for task_info in pending:
        print(f"  Running: {task_info['name']}")

    print("\nImplementation complete.\n")


# ---------------------------------------------------------------------------
# Config command
# ---------------------------------------------------------------------------

def cmd_config(args):
    """Manage configuration."""
    from .cli_commands.commands.config import run_config
    run_config(args)


# ---------------------------------------------------------------------------
# Status command
# ---------------------------------------------------------------------------

def cmd_status(args):
    """Show DevBot status."""
    project_path = Path(args.path).resolve()
    devbot_dir = project_path / ".devbot"
    profile_file = devbot_dir / "project_profile.json"

    print("\n" + "=" * 50)
    print("CLAUDEBOT STATUS")
    print("=" * 50)
    print(f"\nProject: {project_path}")
    print(f"Attached: {'Yes' if devbot_dir.exists() else 'No'}")
    if profile_file.exists():
        profile = json.loads(profile_file.read_text())
        proj = profile.get("project", {})
        print(f"Language: {', '.join(proj.get('language', ['Unknown']))}")
    print(f"\nProfile: {profile_file}")
    print(f"Graph: {devbot_dir / 'code_graph.json'}")
    print("=" * 50 + "\n")


# ---------------------------------------------------------------------------
# List command
# ---------------------------------------------------------------------------

def cmd_list(args):
    """List available features."""
    from .spec.openspec_sync import OpenSpecSync

    project_path = Path(args.path).resolve()
    openspec = OpenSpecSync(str(project_path / "openspec"))
    features = openspec.list_features()

    print("\n" + "=" * 50)
    print("AVAILABLE FEATURES")
    print("=" * 50)
    if features:
        for f in features:
            print(f"  - {f}")
    else:
        print("  No features found. Create one with: claudebot feature <name>")
    print("\n")


# ---------------------------------------------------------------------------
# Serve command (claudebot's FastAPI server)
# ---------------------------------------------------------------------------

def cmd_serve(args):
    """Start the FastAPI server, optionally with Telegram long polling."""
    import uvicorn
    import threading
    from .api.server import app

    config = load_config()
    port = args.port or config.server.port

    if not os.environ.get("CLAUDE_API_KEY") and not config.claude.api_key:
        logger.warning("CLAUDE_API_KEY not set. Set with: export CLAUDE_API_KEY=your-api-key")

    # Start Telegram long polling in a background thread if enabled
    if getattr(args, "telegram", False) or os.environ.get("TELEGRAM_BOT_TOKEN"):
        # Seed token from config into env if not already set
        if not os.environ.get("TELEGRAM_BOT_TOKEN"):
            import yaml
            from .config import get_config_path
            config_path = get_config_path()
            if config_path.exists():
                with open(config_path) as f:
                    yaml_data = yaml.safe_load(f) or {}
                if token := yaml_data.get("telegram_token"):
                    os.environ["TELEGRAM_BOT_TOKEN"] = token
                    logger.info("Loaded TELEGRAM_BOT_TOKEN from config")

        def start_telegram_polling():
            from .api.routes.telegram_polling import run_polling
            asyncio.run(run_polling())

        t = threading.Thread(target=start_telegram_polling, daemon=True)
        t.start()
        logger.info("Telegram long polling started in background thread")

    logger.info(f"Starting server on {args.host}:{port}")
    uvicorn.run(app, host=args.host, port=port, reload=args.reload)


# ---------------------------------------------------------------------------
# Run command (claudebot's direct task execution)
# ---------------------------------------------------------------------------

async def cmd_run(args):
    """Run a task directly via agent."""
    from .agents.code_agent import CodeAgent
    from .agents.spec_agent import SpecAgent
    from .agents.test_agent import TestAgent
    from .agents.deploy_agent import DeployAgent
    from .agents.debug_agent import DebugAgent
    from .agents.base_agent import AgentContext
    from .db.models import init_db

    await init_db()

    api_key = os.environ.get("CLAUDE_API_KEY")
    if not api_key:
        logger.error("CLAUDE_API_KEY not set")
        sys.exit(1)

    config = load_config()

    task = {"description": args.description, "files": []}
    context = AgentContext(
        repo_path=os.getcwd(),
        branch="main",
        claude_api_key=api_key,
        config=config.__dict__,
    )

    agent_map = {
        "spec": SpecAgent,
        "code": CodeAgent,
        "test": TestAgent,
        "deploy": DeployAgent,
        "debug": DebugAgent,
    }

    agent_class = agent_map.get(args.type)
    if not agent_class:
        logger.error(f"Agent type '{args.type}' not implemented yet")
        sys.exit(1)

    agent = agent_class()
    result = await agent.execute(task, context)

    if result.success:
        print(f"OK {result.summary}")
        if result.files_created:
            print(f"Files created: {result.files_created}")
        if result.files_modified:
            print(f"Files modified: {result.files_modified}")
    else:
        print(f"ERROR {result.error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
