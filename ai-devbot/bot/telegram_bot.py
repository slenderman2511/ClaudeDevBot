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

        self._router = CommandRouter(config.get('workflow', {}))
        self._orchestrator = Orchestrator(config.get('workflow', {}))
        self._planner = TaskPlanner(config.get('workflow', {}))
        self._permission_manager = PermissionManager(config.get('guardrails', {}).get('permissions', {}))
        self._validator = CommandValidator(config.get('guardrails', {}).get('command_validation', {}))

        # Initialize Claude CLI tool
        claude_config = config.get('claude', {})
        claude_config['project_context'] = config.get('claude', {}).get('project_context', '.')
        self._claude_tool = ClaudeCLITool(claude_config)

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

I can help you with development tasks:
• /spec - Generate specification documents
• /code - Write implementation code
• /test - Run tests
• /debug - Debug issues
• /deploy - Deploy services
• /status - Check system status
• /help - Show this message

Just send a command with your request!
"""
        await update.message.reply_text(welcome_text)

    async def help_command(self, update: 'Update', context: Any):
        """Handle /help command."""
        help_text = self._router.get_help_text()
        await update.message.reply_text(help_text)

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
        return result

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
        self._application.add_handler(CommandHandler("spec", self.spec_command))
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
