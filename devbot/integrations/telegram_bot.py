"""
Telegram Bot Integration

Optional Telegram bot for DevBot.
"""

import os
import sys
import logging
from typing import Any, Dict, Optional

# Configure logging
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


class DevBotTelegramBot:
    """
    Telegram bot for DevBot.

    Provides remote control of DevBot via Telegram.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the bot.

        Args:
            config: Bot configuration
        """
        if not TELEGRAM_AVAILABLE:
            raise ImportError("python-telegram-bot is required. Install with: pip install python-telegram-bot")

        self.config = config
        self.bot_token = config.get('telegram', {}).get('bot_token', '')

        if not self.bot_token:
            raise ValueError("Bot token is required. Set TELEGRAM_BOT_TOKEN environment variable.")

        # Initialize DevBot
        from devbot import DevBot
        project_path = config.get('project_path', '.')
        self.devbot = DevBot(project_path, config)

        # Application
        self._application = None

    def run(self):
        """Run the bot."""
        logger.info("Starting DevBot Telegram bot...")

        self._application = Application.builder().token(self.bot_token).build()

        # Register handlers
        self._application.add_handler(CommandHandler("start", self._start_command))
        self._application.add_handler(CommandHandler("help", self._help_command))
        self._application.add_handler(CommandHandler("scan", self._scan_command))
        self._application.add_handler(CommandHandler("status", self._status_command))
        self._application.add_handler(CommandHandler("feature", self._feature_command))
        self._application.add_handler(CommandHandler("plan", self._plan_command))
        self._application.add_handler(CommandHandler("implement", self._implement_command))

        # Message handler
        self._application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )

        logger.info("Bot is running. Press Ctrl+C to stop.")
        self._application.run_polling(allowed_updates=Update.ALL_TYPES)

    async def _start_command(self, update: Update, context: Any):
        """Handle /start command."""
        await update.message.reply_text(
            "👋 Welcome to DevBot!\n\n"
            "Commands:\n"
            "• /scan - Scan project\n"
            "• /status - Show status\n"
            "• /feature <name> - Create feature\n"
            "• /plan <name> - Plan feature\n"
            "• /implement <name> - Implement feature\n"
            "• /help - Show help"
        )

    async def _help_command(self, update: Update, context: Any):
        """Handle /help command."""
        await update.message.reply_text(
            "📖 DevBot Commands:\n\n"
            "• /scan - Scan project and detect stack\n"
            "• /status - Show DevBot status\n"
            "• /feature <name> - Create a new feature\n"
            "• /plan <feature> - Generate task plan\n"
            "• /implement <feature> - Implement feature\n"
            "• /help - Show this help"
        )

    async def _scan_command(self, update: Update, context: Any):
        """Handle /scan command."""
        await update.message.reply_text("🔄 Scanning project...")

        try:
            result = self.devbot.scan()
            await update.message.reply_text(
                f"✅ Scan complete!\n\n"
                f"Project: {result['project'].get('name')}\n"
                f"Languages: {', '.join(result['project'].get('language', []))}"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def _status_command(self, update: Update, context: Any):
        """Handle /status command."""
        status = self.devbot.get_status()

        await update.message.reply_text(
            f"📊 DevBot Status\n\n"
            f"Project: {status['project_path']}\n"
            f"Claude CLI: {'✅' if status['claude_available'] else '❌'}\n"
            f"Git: {'✅' if status['git_available'] else '❌'}"
        )

    async def _feature_command(self, update: Update, context: Any):
        """Handle /feature command."""
        args = context.args
        if not args:
            await update.message.reply_text("Usage: /feature <name>")
            return

        feature_name = args[0]
        description = ' '.join(args[1:]) if len(args) > 1 else ""

        await update.message.reply_text(f"🔄 Creating feature: {feature_name}")

        try:
            result = self.devbot.create_feature(feature_name, description)
            await update.message.reply_text(f"✅ Feature created: {feature_name}")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def _plan_command(self, update: Update, context: Any):
        """Handle /plan command."""
        args = context.args
        if not args:
            await update.message.reply_text("Usage: /plan <feature>")
            return

        feature_name = args[0]
        await update.message.reply_text(f"🔄 Planning: {feature_name}")

        try:
            result = self.devbot.plan_feature(feature_name)
            if result.get('success'):
                await update.message.reply_text(f"✅ Plan generated for {feature_name}")
            else:
                await update.message.reply_text(f"❌ {result.get('error')}")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def _implement_command(self, update: Update, context: Any):
        """Handle /implement command."""
        args = context.args
        if not args:
            await update.message.reply_text("Usage: /implement <feature>")
            return

        feature_name = args[0]
        await update.message.reply_text(f"🚀 Implementing: {feature_name}")

        try:
            import asyncio
            result = asyncio.run(self.devbot.implement_feature(feature_name))
            if result.get('success'):
                await update.message.reply_text(
                    f"✅ Implementation complete!\n"
                    f"Completed: {result.get('completed_tasks')} tasks"
                )
            else:
                await update.message.reply_text(f"❌ {result.get('error')}")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def _handle_message(self, update: Update, context: Any):
        """Handle regular messages."""
        await update.message.reply_text(
            "I received your message! Use /help for available commands."
        )


def create_bot(config: Dict[str, Any]) -> DevBotTelegramBot:
    """
    Create a Telegram bot instance.

    Args:
        config: Configuration dictionary

    Returns:
        DevBotTelegramBot instance
    """
    return DevBotTelegramBot(config)


def main():
    """Main entry point for Telegram bot."""
    config = {}

    # Load from environment
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if bot_token:
        config['telegram'] = {'bot_token': bot_token}

    project_path = os.environ.get('PROJECT_PATH', '.')
    config['project_path'] = project_path

    bot = create_bot(config)
    bot.run()


if __name__ == "__main__":
    main()
