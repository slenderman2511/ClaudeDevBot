"""
Telegram Bot Module

Main Telegram bot entry point for AI DevBot.
Uses python-telegram-bot library for polling.
"""

import os
import sys
import logging
import asyncio
from typing import Any, Dict, Optional, TYPE_CHECKING

# Configure logging before imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Check if telegram is available
TELEGRAM_AVAILABLE = False
try:
    from telegram import Update
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        filters,
        ContextTypes,
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    logger.warning("python-telegram-bot not installed. Install with: pip install python-telegram-bot")


# Type hints only - won't fail if telegram not installed
if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes


class AIDevBot:
    """
    Main Telegram bot for AI DevBot.

    Handles incoming messages, routes commands, and coordinates execution.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the bot.

        Args:
            config: Bot configuration
        """
        self.config = config
        self.bot_token = config.get('telegram', {}).get('bot_token', '')

        if not self.bot_token:
            logger.warning("No bot token configured. Set TELEGRAM_BOT_TOKEN environment variable.")

        # Initialize components
        from workflows.command_router import CommandRouter, CommandType
        from workflows.orchestration import Orchestrator
        from workflows.task_planner import TaskPlanner
        from guardrails.permissions import PermissionManager
        from guardrails.command_validation import CommandValidator
        from tools.claude_cli import ClaudeCLITool
        from openspec import get_openspec
        from memory import get_memory

        self._router = CommandRouter(config.get('workflow', {}))
        self._orchestrator = Orchestrator(config.get('workflow', {}))
        self._planner = TaskPlanner(config.get('workflow', {}))
        self._permission_manager = PermissionManager(config.get('guardrails', {}).get('permissions', {}))
        self._validator = CommandValidator(config.get('guardrails', {}).get('command_validation', {}))

        # Initialize Claude CLI tool
        claude_config = config.get('claude', {})
        claude_config['project_context'] = config.get('claude', {}).get('project_context', '.')
        self._claude_tool = ClaudeCLITool(claude_config)

        # Initialize OpenSpec
        self._openspec = get_openspec(config.get('openspec_path', 'openspec'))

        # Initialize Memory
        self._memory = get_memory()

        # Setup handlers
        self._setup_handlers()

        # Bot application
        self._application = None

        # Track user tasks
        self._user_tasks: Dict[int, str] = {}  # user_id -> task_description

        logger.info("AI DevBot initialized")

    def _setup_handlers(self):
        """Setup command handlers."""
        from workflows.command_router import CommandType

        # Register command handlers
        self._router.register_handler(CommandType.SPEC, self._handle_spec)
        self._router.register_handler(CommandType.CODE, self._handle_code)
        self._router.register_handler(CommandType.TEST, self._handle_test)
        self._router.register_handler(CommandType.DEPLOY, self._handle_deploy)
        self._router.register_handler(CommandType.DEBUG, self._handle_debug)
        self._router.register_handler(CommandType.STATUS, self._handle_status)
        self._router.register_handler(CommandType.HELP, self._handle_help)

    async def start_command(self, update: 'Update', context: Any):
        """Handle /start command."""
        welcome_text = """
👋 Welcome to AI DevBot!

Spec-Driven AI Development with OpenSpec

📋 Features:
• /feature create <name> - Create feature
• /feature list - List features
• /feature show <name> - Show details

📝 Specification:
• /spec plan <feature> - Plan/specify
• /tasks list <feature> - List tasks

💻 Workflow:
• /code implement <feature>
• /test run
• /deploy staging|production
• /debug <service>
• /status

Type /help for all commands!
"""
        await update.message.reply_text(welcome_text)

    async def help_command(self, update: 'Update', context: Any):
        """Handle /help command."""
        help_text = """
🤖 AI DevBot Commands:

📋 Feature Management:
• /feature create <name> - Create new feature
• /feature list - List all features
• /feature show <name> - Show feature details

📝 Specification:
• /spec plan <feature> - Plan/specify a feature

📋 Task Management:
• /tasks list <feature> - List pending tasks
• /tasks show <feature> - Show task graph

💻 Code:
• /code implement <feature> - Generate code for feature

🧪 Testing:
• /test run - Run tests

🚀 Deployment:
• /deploy staging - Deploy to staging
• /deploy production - Deploy to production

🔧 Debugging:
• /debug <service> - Debug a service

📊 Status:
• /status - Show system status
"""
        await update.message.reply_text(help_text)

    async def feature_command(self, update: 'Update', context: Any):
        """Handle /feature command - create, list, show features."""
        user_id = update.effective_user.id
        if not self._permission_manager.is_allowed(user_id):
            await update.message.reply_text("❌ You are not authorized to use this bot.")
            return

        args = ' '.join(context.args) if context.args else ""

        if not args:
            await update.message.reply_text(
                "📋 Usage:\n• /feature create <name> - Create feature\n• /feature list - List features\n• /feature show <name> - Show details"
            )
            return

        # Parse subcommand
        parts = args.split(None, 1)
        subcommand = parts[0].lower()
        feature_name = parts[1] if len(parts) > 1 else ""

        if subcommand == "create" and feature_name:
            # Create new feature
            await update.message.reply_text(f"🔄 Creating feature: {feature_name}")
            try:
                spec = self._openspec.create_feature(feature_name, f"Feature: {feature_name}")
                await update.message.reply_text(
                    f"✅ Feature '{feature_name}' created!\n\n"
                    f"Status: {spec.get('status', 'draft')}\n"
                    f"Tasks: {len(spec.get('tasks', []))}"
                )
            except Exception as e:
                await update.message.reply_text(f"❌ Error creating feature: {e}")

        elif subcommand == "list":
            # List all features
            features = self._openspec.list_features()
            if features:
                msg = "📋 Features:\n" + "\n".join(f"• {f}" for f in features)
            else:
                msg = "No features found. Create one with /feature create <name>"
            await update.message.reply_text(msg)

        elif subcommand == "show" and feature_name:
            # Show feature details
            spec = self._openspec.load_feature(feature_name)
            if spec:
                validation = self._openspec.validate_spec(feature_name)
                pending = self._openspec.get_pending_tasks(feature_name)
                msg = f"""📋 Feature: {feature_name}

Status: {spec.get('status', 'unknown')}
Version: {spec.get('version', '1.0.0')}
Tasks: {validation['stats']['completed_tasks']}/{validation['stats']['total_tasks']} ({validation['stats']['progress']})

Pending Tasks:
"""
                for task in pending[:5]:
                    msg += f"• [{task['phase']}] {task['name']}\n"
                if len(pending) > 5:
                    msg += f"... and {len(pending) - 5} more"
                await update.message.reply_text(msg)
            else:
                await update.message.reply_text(f"❌ Feature '{feature_name}' not found")

        else:
            await update.message.reply_text("Unknown subcommand. Use: create, list, or show")

    async def tasks_command(self, update: 'Update', context: Any):
        """Handle /tasks command - list or show tasks."""
        user_id = update.effective_user.id
        if not self._permission_manager.is_allowed(user_id):
            await update.message.reply_text("❌ You are not authorized to use this bot.")
            return

        args = ' '.join(context.args) if context.args else ""

        if not args:
            await update.message.reply_text(
                "📋 Usage:\n• /tasks list <feature> - List pending tasks\n• /tasks show <feature> - Show task graph"
            )
            return

        parts = args.split(None, 1)
        subcommand = parts[0].lower()
        feature_name = parts[1] if len(parts) > 1 else ""

        if subcommand == "list" and feature_name:
            pending = self._openspec.get_pending_tasks(feature_name)
            if pending:
                msg = f"📋 Pending tasks for '{feature_name}':\n\n"
                for task in pending:
                    msg += f"• [{task['phase']}] {task['name']}\n"
                await update.message.reply_text(msg)
            else:
                await update.message.reply_text(f"✅ No pending tasks for '{feature_name}'")

        elif subcommand == "show" and feature_name:
            graph = self._openspec.get_task_graph(feature_name)
            if "error" in graph:
                await update.message.reply_text(f"❌ {graph['error']}")
            else:
                msg = f"""📋 Task Graph: {feature_name}

Total: {graph['total_tasks']} tasks
Completed: {graph['completed_tasks']}
Status: {graph['status']}

Phases:
"""
                for phase, tasks in graph.get('phases', {}).items():
                    completed = sum(1 for t in tasks if t.get('completed'))
                    msg += f"\n{phase}: {completed}/{len(tasks)}\n"
                    for task in tasks:
                        status = "✅" if task.get('completed') else "⬜"
                        msg += f"  {status} {task['name']}\n"
                await update.message.reply_text(msg)

        else:
            await update.message.reply_text("Unknown subcommand. Use: list or show")

    async def spec_command(self, update: 'Update', context: Any):
        """Handle /spec command."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        # Check permissions
        if not self._permission_manager.is_allowed(user_id):
            await update.message.reply_text("❌ You are not authorized to use this bot.")
            return

        # Get arguments
        args = ' '.join(context.args) if context.args else ""

        if not args:
            await update.message.reply_text(
                "📝 Usage: /spec <description>\n\nExample: /spec Create a user authentication system"
            )
            return

        # Acknowledge
        await update.message.reply_text(f"🔄 Generating specification for: {args[:50]}...")

        try:
            # Execute spec generation
            result = await self._execute_spec(args)

            if result.success:
                # Send result (truncate if too long)
                response = result.output.get('response', str(result.output))[:4000]
                await update.message.reply_text(f"✅ Specification generated:\n\n{response}")
            else:
                await update.message.reply_text(f"❌ Error: {result.error}")

        except Exception as e:
            logger.exception("Error in spec command")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def code_command(self, update: 'Update', context: Any):
        """Handle /code command."""
        user_id = update.effective_user.id

        # Check permissions
        if not self._permission_manager.is_allowed(user_id):
            await update.message.reply_text("❌ You are not authorized to use this bot.")
            return

        # Get arguments
        args = ' '.join(context.args) if context.args else ""

        if not args:
            await update.message.reply_text(
                "💻 Usage: /code <requirement>\n\nExample: /code Create a REST API for users"
            )
            return

        # Acknowledge
        await update.message.reply_text(f"🔄 Generating code for: {args[:50]}...")

        try:
            result = await self._execute_code(args)

            if result.success:
                response = result.output.get('response', str(result.output))[:4000]
                await update.message.reply_text(f"✅ Code generated:\n\n{response}")
            else:
                await update.message.reply_text(f"❌ Error: {result.error}")

        except Exception as e:
            logger.exception("Error in code command")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def test_command(self, update: 'Update', context: Any):
        """Handle /test command."""
        user_id = update.effective_user.id

        if not self._permission_manager.is_allowed(user_id):
            await update.message.reply_text("❌ You are not authorized to use this bot.")
            return

        args = ' '.join(context.args) if context.args else "all"

        await update.message.reply_text(f"🔄 Running tests for: {args}...")

        try:
            result = await self._execute_test(args)

            if result.success:
                response = result.output.get('response', str(result.output))[:4000]
                await update.message.reply_text(f"✅ Tests completed:\n\n{response}")
            else:
                await update.message.reply_text(f"❌ Error: {result.error}")

        except Exception as e:
            logger.exception("Error in test command")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def debug_command(self, update: 'Update', context: Any):
        """Handle /debug command."""
        user_id = update.effective_user.id

        if not self._permission_manager.is_allowed(user_id):
            await update.message.reply_text("❌ You are not authorized to use this bot.")
            return

        args = ' '.join(context.args) if context.args else ""

        if not args:
            await update.message.reply_text(
                "🐛 Usage: /debug <error description>\n\nExample: /debug Connection refused on port 3000"
            )
            return

        await update.message.reply_text(f"🔄 Analyzing issue: {args[:50]}...")

        try:
            result = await self._execute_debug(args)

            if result.success:
                response = result.output.get('response', str(result.output))[:4000]
                await update.message.reply_text(f"✅ Debug analysis:\n\n{response}")
            else:
                await update.message.reply_text(f"❌ Error: {result.error}")

        except Exception as e:
            logger.exception("Error in debug command")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def deploy_command(self, update: 'Update', context: Any):
        """Handle /deploy command."""
        user_id = update.effective_user.id

        if not self._permission_manager.is_allowed(user_id):
            await update.message.reply_text("❌ You are not authorized to use this bot.")
            return

        args = ' '.join(context.args) if context.args else "staging"

        await update.message.reply_text(f"🚀 Deploying to: {args}...")

        try:
            result = await self._execute_deploy(args)

            if result.success:
                response = result.output.get('response', str(result.output))[:4000]
                await update.message.reply_text(f"✅ Deployment completed:\n\n{response}")
            else:
                await update.message.reply_text(f"❌ Error: {result.error}")

        except Exception as e:
            logger.exception("Error in deploy command")
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def status_command(self, update: 'Update', context: Any):
        """Handle /status command."""
        # Get Claude CLI status
        claude_available = self._claude_tool.validate()

        status_text = f"""
📊 AI DevBot Status

Claude CLI: {'✅ Available' if claude_available else '❌ Not found'}
Bot: ✅ Running
Commands processed: {len(self._user_tasks)}

Registered agents:
• spec_agent - Generate specifications
• code_agent - Generate code
• test_agent - Run tests
• deploy_agent - Deploy services
• debug_agent - Debug issues
"""
        await update.message.reply_text(status_text)

    async def handle_message(self, update: 'Update', context: Any):
        """Handle regular messages (not commands)."""
        # Check if it's a command
        if update.message.text.startswith('/'):
            await update.message.reply_text("Unknown command. Use /help for available commands.")
            return

        # Echo for now - can be extended for conversational AI
        await update.message.reply_text(
            "I received your message! Use /help to see available commands."
        )

    # Execution methods - integrate with Claude CLI
    async def _execute_spec(self, requirement: str):
        """Execute specification generation."""
        prompt = f"""Generate a detailed specification document for the following requirement:

{requirement}

Include:
1. Overview
2. Functional requirements
3. Non-functional requirements
4. User stories
5. Technical considerations
"""

        result = self._claude_tool.execute(prompt, task_type='spec')

        # Save spec to file if successful
        if result.success and result.output:
            spec_content = result.output.get('response', '')
            spec_path = self._save_spec(requirement, spec_content)
            if spec_path:
                logger.info(f"Spec saved to: {spec_path}")

        return result

    def _save_spec(self, requirement: str, content: str) -> str:
        """Save specification to a file."""
        import re
        from datetime import datetime

        # Create slug from requirement
        slug = re.sub(r'[^a-zA-Z0-9]+', '-', requirement.lower())
        slug = slug.strip('-')[:50]

        # Create filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        filename = f"{timestamp}-{slug}.md"

        # Get specs directory
        specs_dir = self.config.get('specs_dir', 'specs')
        os.makedirs(specs_dir, exist_ok=True)

        filepath = os.path.join(specs_dir, filename)

        # Write spec to file
        try:
            with open(filepath, 'w') as f:
                f.write(f"# Specification: {requirement}\n\n")
                f.write(content)
            return filepath
        except Exception as e:
            logger.error(f"Failed to save spec: {e}")
            return ""

    async def _execute_code(self, requirement: str):
        """Execute code generation."""
        prompt = f"""Generate implementation code for the following requirement:

{requirement}

Provide clean, well-documented code with appropriate comments.
"""

        result = self._claude_tool.execute(prompt, task_type='code')
        return result

    async def _execute_test(self, scope: str):
        """Execute tests."""
        prompt = f"""Run tests for the following scope:

{scope}

Execute the tests and report the results.
"""

        result = self._claude_tool.execute(prompt, task_type='test')
        return result

    async def _execute_debug(self, issue: str):
        """Execute debugging."""
        prompt = f"""Analyze and help debug the following issue:

{issue}

Provide:
1. Possible causes
2. Debugging steps
3. Suggested fixes
"""

        result = self._claude_tool.execute(prompt, task_type='debug')
        return result

    async def _execute_deploy(self, target: str):
        """Execute deployment."""
        prompt = f"""Deploy to the following target:

{target}

Provide deployment steps and status updates.
"""

        result = self._claude_tool.execute(prompt, task_type='deploy')
        return result

    # Legacy handlers (for compatibility)
    async def _handle_spec(self, parsed) -> str:
        return "Use /spec command"

    async def _handle_code(self, parsed) -> str:
        return "Use /code command"

    async def _handle_test(self, parsed) -> str:
        return "Use /test command"

    async def _handle_deploy(self, parsed) -> str:
        return "Use /deploy command"

    async def _handle_debug(self, parsed) -> str:
        return "Use /debug command"

    async def _handle_status(self, parsed) -> str:
        return "Use /status command"

    async def _handle_help(self, parsed) -> str:
        return self._router.get_help_text()

    def run(self):
        """Run the bot using polling."""
        if not TELEGRAM_AVAILABLE:
            logger.error("python-telegram-bot not available. Cannot start bot.")
            print("ERROR: python-telegram-bot not installed.")
            print("Install with: pip install python-telegram-bot")
            sys.exit(1)

        if not self.bot_token:
            logger.error("No bot token configured. Set TELEGRAM_BOT_TOKEN environment variable.")
            print("ERROR: No bot token configured.")
            print("Set TELEGRAM_BOT_TOKEN environment variable or configure in config.yaml")
            sys.exit(1)

        # Import here to ensure availability
        from telegram import Update
        from telegram.ext import (
            Application,
            CommandHandler,
            MessageHandler,
            filters,
        )

        logger.info("Starting AI DevBot...")

        # Create application
        self._application = Application.builder().token(self.bot_token).build()

        # Register handlers
        self._application.add_handler(CommandHandler("start", self.start_command))
        self._application.add_handler(CommandHandler("help", self.help_command))
        # New OpenSpec commands
        self._application.add_handler(CommandHandler("feature", self.feature_command))
        self._application.add_handler(CommandHandler("spec", self.spec_command))
        self._application.add_handler(CommandHandler("tasks", self.tasks_command))
        # Existing workflow commands
        self._application.add_handler(CommandHandler("code", self.code_command))
        self._application.add_handler(CommandHandler("test", self.test_command))
        self._application.add_handler(CommandHandler("debug", self.debug_command))
        self._application.add_handler(CommandHandler("deploy", self.deploy_command))
        self._application.add_handler(CommandHandler("status", self.status_command))

        # Handle regular messages
        self._application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        # Start polling
        logger.info("Bot is running. Press Ctrl+C to stop.")
        self._application.run_polling(allowed_updates=Update.ALL_TYPES)

    async def stop(self):
        """Stop the bot."""
        if self._application:
            await self._application.stop()


def create_bot(config: Dict[str, Any]) -> AIDevBot:
    """
    Create and configure the bot.

    Args:
        config: Configuration dictionary

    Returns:
        Configured AIDevBot instance
    """
    return AIDevBot(config)


def main():
    """Main entry point."""
    # Load config
    config_path = os.environ.get('CONFIG_PATH', 'config/config.yaml')

    config = {}
    if os.path.exists(config_path):
        try:
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Could not load config: {e}")

    # Override with environment variables
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if bot_token:
        if 'telegram' not in config:
            config['telegram'] = {}
        config['telegram']['bot_token'] = bot_token

    # Create and run bot
    bot = create_bot(config)
    bot.run()


if __name__ == "__main__":
    main()
