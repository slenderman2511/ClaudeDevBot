"""
Telegram long polling bot — runs independently of the FastAPI server.
Use: claudebot serve --telegram
"""

import os
import logging
import asyncio

from telegram import Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)
from telegram.error import Forbidden, RetryAfter

from . import telegram as telegram_routes

logger = logging.getLogger(__name__)

# Re-use the response logic from the webhook routes
# We copy the key functions we need rather than import the entire module
# to avoid circular imports with the FastAPI app.


async def handle_start(update, context):
    """Handle /start command."""
    text = telegram_routes.format_start()
    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_help(update, context):
    """Handle /help command."""
    text = telegram_routes.format_help()
    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_spec(update, context):
    """Handle /spec command."""
    args = context.args
    if not args:
        await update.message.reply_text(
            "⚠️ Please provide a description.\nUsage: /spec <description>",
            parse_mode="Markdown",
        )
        return
    await create_agent_task(update, "spec", " ".join(args))


async def handle_code(update, context):
    """Handle /code command."""
    args = context.args
    if not args:
        await update.message.reply_text(
            "⚠️ Please provide a description.\nUsage: /code <description>",
            parse_mode="Markdown",
        )
        return
    await create_agent_task(update, "code", " ".join(args))


async def handle_test(update, context):
    """Handle /test command."""
    args = context.args
    if not args:
        await update.message.reply_text(
            "⚠️ Please provide a description.\nUsage: /test <description>",
            parse_mode="Markdown",
        )
        return
    await create_agent_task(update, "test", " ".join(args))


async def handle_deploy(update, context):
    """Handle /deploy command."""
    args = context.args
    if not args:
        await update.message.reply_text(
            "⚠️ Please provide a description.\nUsage: /deploy <description>",
            parse_mode="Markdown",
        )
        return
    await create_agent_task(update, "deploy", " ".join(args))


async def handle_debug(update, context):
    """Handle /debug command."""
    args = context.args
    if not args:
        await update.message.reply_text(
            "⚠️ Please provide a description.\nUsage: /debug <description>",
            parse_mode="Markdown",
        )
        return
    await create_agent_task(update, "debug", " ".join(args))


async def handle_status(update, context):
    """Handle /status command."""
    args = context.args
    if not args:
        await update.message.reply_text(
            "⚠️ Please provide a task ID.\nUsage: /status <task_id>",
            parse_mode="Markdown",
        )
        return

    task_id = args[0]
    manager = telegram_routes.get_task_manager()

    if not manager:
        await update.message.reply_text(
            "⚠️ Task manager not initialized. Please start the server first.",
            parse_mode="Markdown",
        )
        return

    try:
        task = await manager.get_task_status(task_id)
        if task:
            from .tasks import get_task_manager
            text = telegram_routes.format_task_response({
                "id": task.id,
                "type": task.type.value,
                "status": task.status.value,
                "description": task.description,
                "created_at": task.created_at,
                "error": task.error,
                "result": task.result,
            })
        else:
            text = f"❌ Task not found: {task_id}"
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        logger.exception(f"Failed to get task status: {e}")
        await update.message.reply_text(f"❌ Error: {e}", parse_mode="Markdown")


async def handle_cancel(update, context):
    """Handle /cancel command."""
    args = context.args
    if not args:
        await update.message.reply_text(
            "⚠️ Please provide a task ID.\nUsage: /cancel <task_id>",
            parse_mode="Markdown",
        )
        return

    task_id = args[0]
    manager = telegram_routes.get_task_manager()

    if not manager:
        await update.message.reply_text(
            "⚠️ Task manager not initialized. Please start the server first.",
            parse_mode="Markdown",
        )
        return

    try:
        success = await manager.cancel_task(task_id)
        if success:
            text = f"✅ Task cancelled: {task_id}"
        else:
            text = f"⚠️ Could not cancel task (may not be running): {task_id}"
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        logger.exception(f"Failed to cancel task: {e}")
        await update.message.reply_text(f"❌ Error: {e}", parse_mode="Markdown")


async def handle_message(update, context):
    """Handle plain text messages."""
    text = update.message.text.strip()
    if not text.startswith("/"):
        # Ignore non-command messages
        return
    await update.message.reply_text(
        "Unknown command. Type /help for available commands.",
        parse_mode="Markdown",
    )


async def create_agent_task(update, task_type: str, description: str):
    """Create a task via task manager and reply with task info."""
    manager = telegram_routes.get_task_manager()
    if not manager:
        await update.message.reply_text(
            "⚠️ Task manager not initialized. Please start the server first.",
            parse_mode="Markdown",
        )
        return

    try:
        task_data = {
            "type": task_type,
            "description": description,
            "files": [],
            "branch": "main",
            "priority": 0,
        }
        task = await manager.create_task(task_data)
        text = (
            f"✅ Task created!\n\n"
            f"*Task ID:* `{task.id}`\n"
            f"*Type:* {task_type}\n"
            f"*Description:* {description}\n\n"
            f"Check status with /status {task.id}"
        )
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        logger.exception(f"Failed to create task: {e}")
        await update.message.reply_text(
            f"❌ Failed to create task: {e}",
            parse_mode="Markdown",
        )


async def error_handler(update, context):
    """Handle errors from the dispatcher."""
    try:
        raise context.error
    except Forbidden:
        logger.warning(f"Bot blocked by user {getattr(update, 'effective_chat', None)}")
    except RetryAfter as e:
        logger.warning(f"Rate limited by Telegram, retry after {e.retry_after}s")
        await asyncio.sleep(e.retry_after)
    except Exception:
        logger.exception(f"Telegram polling error: {context.error}")


def run_polling():
    """Start the Telegram bot with long polling (blocking).

    Creates its own event loop and runs it forever.
    Call from a daemon thread — do NOT wrap with asyncio.run().
    """
    import signal

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set — cannot start Telegram polling")
        return

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _build_and_run():
        """Build PTB app and run polling on this same loop."""
        app = (
            Application.builder()
            .token(token)
            .read_timeout(30)
            .write_timeout(30)
            .build()
        )

        # Register handlers
        app.add_handler(CommandHandler("start", handle_start))
        app.add_handler(CommandHandler("help", handle_help))
        app.add_handler(CommandHandler("spec", handle_spec))
        app.add_handler(CommandHandler("code", handle_code))
        app.add_handler(CommandHandler("test", handle_test))
        app.add_handler(CommandHandler("deploy", handle_deploy))
        app.add_handler(CommandHandler("debug", handle_debug))
        app.add_handler(CommandHandler("status", handle_status))
        app.add_handler(CommandHandler("cancel", handle_cancel))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.add_error_handler(error_handler)

        logger.info("Starting Telegram long polling bot...")

        # Initialise and start polling
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        logger.info("Telegram bot handlers registered — polling for updates...")

        # Keep running until cancelled
        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            pass
        finally:
            await app.updater.stop_polling()
            await app.stop()
            await app.shutdown()

    # run_forever so the loop stays alive for the lifetime of the daemon thread
    # Schedule _build_and_run() on the loop before running it forever.
    # It will keep the loop alive with its infinite sleep.
    asyncio.ensure_future(_build_and_run(), loop=loop)
    try:
        loop.run_forever()
    finally:
        loop.close()
