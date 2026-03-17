# .claudebot/cli.py
"""CLI entry point for ClaudeDevBot Plugin"""

import sys
import os
import asyncio
import logging

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.server import app
from db.models import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    """Main CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="ClaudeDevBot Plugin CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # serve command
    serve_parser = subparsers.add_parser("serve", help="Start API server")
    serve_parser.add_argument("--host", default="localhost", help="Host to bind")
    serve_parser.add_argument("--port", type=int, default=8765, help="Port to bind")
    serve_parser.add_argument("--reload", action="store_true", help="Auto-reload")

    # run command
    run_parser = subparsers.add_parser("run", help="Run a task directly")
    run_parser.add_argument("type", choices=["spec", "code", "test", "deploy", "debug"], help="Task type")
    run_parser.add_argument("description", help="Task description")

    args = parser.parse_args()

    if args.command == "serve":
        asyncio.run(serve(args))
    elif args.command == "run":
        asyncio.run(run_task(args))
    else:
        parser.print_help()

async def serve(args):
    """Start the API server"""
    import uvicorn

    # Initialize database
    await init_db()

    # Validate config
    if not os.environ.get("CLAUDE_API_KEY"):
        logger.warning("CLAUDE_API_KEY not set. Set with: export CLAUDE_API_KEY=your-api-key")

    logger.info(f"Starting server on {args.host}:{args.port}")

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload
    )

async def run_task(args):
    """Run a task directly"""
    from agents.code_agent import CodeAgent
    from agents.base_agent import AgentContext
    from db.models import init_db

    await init_db()

    api_key = os.environ.get("CLAUDE_API_KEY")
    if not api_key:
        logger.error("CLAUDE_API_KEY not set")
        sys.exit(1)

    task = {
        "type": args.type,
        "description": args.description,
        "files": []
    }

    context = AgentContext(
        repo_path=os.getcwd(),
        branch="main",
        claude_api_key=api_key,
        config={}
    )

    agent = CodeAgent()
    result = await agent.execute(task, context)

    if result.success:
        print(f"✓ {result.summary}")
        print(f"Files: {result.files_modified}")
    else:
        print(f"✗ {result.error}")
        sys.exit(1)

if __name__ == "__main__":
    main()
