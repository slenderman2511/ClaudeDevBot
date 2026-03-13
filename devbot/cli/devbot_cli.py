"""
DevBot CLI

Command-line interface for DevBot.
"""

import sys
import os
import asyncio
import json
from pathlib import Path
from typing import Optional

import click

from devbot.core.devbot_core import DevBot, create_devbot
from devbot.observability.logger import get_logger, configure_logging

# Configure logging
configure_logging()
logger = get_logger(__name__)


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """
    DevBot - AI Engineering Teammate

    A CLI plugin that attaches to any repository and provides AI-assisted
    development using OpenSpec and Claude Code.
    """
    pass


@cli.command()
@click.argument("path", default=".")
def attach(path: str):
    """
    Attach DevBot to a repository.

    Creates .devbot folder and project profile.

    Example:

        devbot attach .
        devbot attach /path/to/project
    """
    try:
        bot = create_devbot(path)
        result = bot.attach()

        click.echo(f"✅ Attached to project: {result['project']['name']}")
        click.echo(f"   Path: {result['project']['path']}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--path", default=".", help="Project path to scan")
def scan(path: str):
    """
    Scan the project and detect tech stack.

    Identifies:
    - Programming languages
    - Frameworks
    - Dependencies
    - Configuration files

    Example:

        devbot scan
        devbot scan --path /path/to/project
    """
    try:
        bot = create_devbot(path)
        result = bot.scan()

        click.echo("\n📊 Project Scan Results\n")
        click.echo(f"Project: {result['project'].get('name', 'Unknown')}")
        click.echo(f"Languages: {', '.join(result['project'].get('language', []))}")

        # Show stack info
        if result.get('stack'):
            stack = result['stack']
            if stack.get('frameworks'):
                click.echo(f"Frameworks: {', '.join([f['name'] for f in stack['frameworks']])}")
            if stack.get('tools'):
                click.echo(f"Tools: {', '.join(stack['tools'])}")

        click.echo(f"\n✅ Scan complete. Profile saved to .devbot/project_profile.json")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--path", default=".", help="Project path")
def graph(path: str):
    """
    Build a code knowledge graph.

    Creates nodes for:
    - Files
    - Classes
    - Functions

    Creates edges for:
    - Imports
    - Dependencies

    Example:

        devbot graph
        devbot graph --path /path/to/project
    """
    try:
        bot = create_devbot(path)
        result = bot.build_graph()

        click.echo("\n🔗 Code Graph Built\n")
        click.echo(f"Nodes: {len(result.get('nodes', {}))}")
        click.echo(f"Edges: {len(result.get('edges', []))}")

        click.echo(f"\n✅ Graph saved to .devbot/code_graph.json")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("feature_name")
@click.option("--description", "-d", default="", help="Feature description")
@click.option("--path", default=".", help="Project path")
def feature(feature_name: str, description: str, path: str):
    """
    Create a new OpenSpec feature.

    Creates a feature specification in openspec/features/.

    Example:

        devbot feature payment-service
        devbot feature user-auth --description "Add user authentication"
    """
    try:
        bot = create_devbot(path)
        result = bot.create_feature(feature_name, description)

        click.echo(f"✅ Feature created: {feature_name}")
        click.echo(f"   File: {result['file']}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("feature_name")
@click.option("--path", default=".", help="Project path")
def plan(feature_name: str, path: str):
    """
    Generate a task plan from OpenSpec feature.

    Creates a task DAG from the feature specification.

    Example:

        devbot plan payment-service
    """
    try:
        bot = create_devbot(path)
        result = bot.plan_feature(feature_name)

        if result.get('success'):
            click.echo(f"\n📋 Plan for: {feature_name}\n")
            click.echo(result['plan'])
            click.echo(f"\n✅ Plan saved to: {result['plan_file']}")
        else:
            click.echo(f"❌ Error: {result.get('error', 'Unknown error')}", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("feature_name")
@click.option("--path", default=".", help="Project path")
def implement(feature_name: str, path: str):
    """
    Implement a feature using AI agents.

    Executes the task plan and generates code via Claude Code.

    Example:

        devbot implement payment-service
    """
    try:
        bot = create_devbot(path)

        click.echo(f"🚀 Implementing feature: {feature_name}")
        click.echo("This may take a while...\n")

        # Run async implementation
        result = asyncio.run(bot.implement_feature(feature_name))

        if result.get('success'):
            click.echo(f"✅ Implementation complete!")
            click.echo(f"   Completed tasks: {result['completed_tasks']}")
        else:
            click.echo(f"❌ Error: {result.get('error', 'Unknown error')}", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--path", default=".", help="Project path")
def status(path: str):
    """
    Show DevBot status.

    Example:

        devbot status
    """
    try:
        bot = create_devbot(path)
        status = bot.get_status()

        click.echo("\n📊 DevBot Status\n")
        click.echo(f"Project: {status['project_path']}")
        click.echo(f"Attached: {'Yes' if status['attached'] else 'No'}")
        click.echo(f"Claude CLI: {'✅ Available' if status['claude_available'] else '❌ Not found'}")
        click.echo(f"Git: {'✅ Available' if status['git_available'] else '❌ Not found'}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command("list")
@click.argument("feature_name", required=False, default=None)
@click.option("--path", default=".", help="Project path")
def list_features(feature_name: Optional[str], path: str):
    """
    List available features.

    Example:

        devbot list
        devbot list payment-service
    """
    try:
        bot = create_devbot(path)
        features = bot.openspec.list_features()

        if features:
            click.echo("\n📋 Available Features:\n")
            for f in features:
                click.echo(f"  • {f}")
        else:
            click.echo("No features found. Create one with: devbot feature <name>")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
