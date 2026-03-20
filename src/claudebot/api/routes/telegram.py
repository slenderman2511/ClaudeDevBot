# .claudebot/api/routes/telegram.py
"""Telegram webhook handler"""

import logging
from typing import Optional
from enum import Enum

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..enums import TaskType

# Re-export for convenience (also used by telegram_polling.py)
from .tasks import get_task_manager

logger = logging.getLogger(__name__)

router = APIRouter()


class CommandType(str, Enum):
    """Supported Telegram commands"""
    START = "start"
    HELP = "help"
    SPEC = "spec"
    CODE = "code"
    TEST = "test"
    DEPLOY = "deploy"
    DEBUG = "debug"
    STATUS = "status"
    CANCEL = "cancel"


def extract_command(text: str) -> tuple[Optional[CommandType], str]:
    """Extract command and arguments from message text"""
    if not text:
        return None, ""

    parts = text.strip().split(maxsplit=1)
    command = parts[0].lower().replace("/", "")
    args = parts[1] if len(parts) > 1 else ""

    command_map = {
        "start": CommandType.START,
        "help": CommandType.HELP,
        "spec": CommandType.SPEC,
        "code": CommandType.CODE,
        "test": CommandType.TEST,
        "deploy": CommandType.DEPLOY,
        "debug": CommandType.DEBUG,
        "status": CommandType.STATUS,
        "cancel": CommandType.CANCEL,
    }

    return command_map.get(command), args


def format_task_response(task: dict) -> str:
    """Format task status as plain-text Telegram message (no Markdown)."""
    status_emoji = {
        "pending": "⏳",
        "queued": "📋",
        "running": "🔄",
        "completed": "✅",
        "failed": "❌",
        "cancelled": "🚫"
    }

    emoji = status_emoji.get(task.get("status", ""), "❓")

    response = f"""
{emoji} Task Status

ID: {task.get('id', 'N/A')}
Type: {task.get('type', 'N/A')}
Status: {task.get('status', 'N/A').upper()}
Description: {task.get('description', 'N/A')}

Created: {task.get('created_at', 'N/A')}
"""

    if task.get("error"):
        response += f"\nError: {task.get('error')}"

    if task.get("result"):
        response += f"\nResult: {task.get('result')}"

    return response


def format_help() -> str:
    """Format help message (plain text, no Markdown)."""
    return """
ClaudeDevBot Commands

/start - Start the bot
/help - Show this help message

AI Agents:
/spec <description> - Generate specification
/code <description> - Generate code
/test <description> - Generate tests
/debug <error> - Debug an error
/deploy <description> - Generate deployment config

Task Management:
/status <task_id> - Check task status
/cancel <task_id> - Cancel a task
"""


def format_start() -> str:
    """Format start message (plain text, no Markdown)."""
    return """
Welcome to ClaudeDevBot!

I'm your AI-powered development assistant. I can help you with:

- 📝 Generating specifications
- 💻 Writing code
- 🧪 Creating tests
- 🐛 Debugging errors
- 🚀 Deployment configs

Type /help to see all commands.
"""


@router.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """Handle Telegram webhook updates"""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Parse update
    message = body.get("message", {})
    callback_query = body.get("callback_query")

    # Handle callback query (inline buttons)
    if callback_query:
        message = callback_query.get("message", {})

    # Get message text and chat
    if not message:
        return {"ok": True}

    text = message.get("text", "")
    chat_id = message.get("chat", {}).get("id")

    if not chat_id or not text:
        return {"ok": True}

    # Extract command
    command, args = extract_command(text)

    # Get task manager
    from .tasks import get_task_manager

    manager = get_task_manager()

    # Process command
    response_text = ""

    if command == CommandType.START:
        response_text = format_start()

    elif command == CommandType.HELP:
        response_text = format_help()

    elif command in [CommandType.SPEC, CommandType.CODE, CommandType.TEST,
                     CommandType.DEPLOY, CommandType.DEBUG]:
        if not args:
            response_text = f"⚠️ Please provide a description.\nUsage: /{command.value} <description>"
        elif manager:
            try:
                task_data = {
                    "type": command.value,
                    "description": args,
                    "files": [],
                    "branch": "main",
                    "priority": 0,
                }
                task = await manager.create_task(task_data)
                response_text = f"✅ Task created!\n\nTask ID: {task.id}\nType: {command.value}\nDescription: {args}\n\nCheck status with /status {task.id}"
            except Exception as e:
                logger.exception("Failed to create task")
                response_text = f"❌ Failed to create task: {str(e)}"
        else:
            response_text = "⚠️ Task manager not initialized. Please start the server first."

    elif command == CommandType.STATUS:
        if not args:
            response_text = "⚠️ Please provide a task ID.\nUsage: /status <task_id>"
        elif manager:
            task = await manager.get_task_status(args)
            if task:
                response_text = format_task_response({
                    "id": task.id,
                    "type": task.type.value,
                    "status": task.status.value,
                    "description": task.description,
                    "created_at": task.created_at,
                    "error": task.error,
                    "result": task.result
                })
            else:
                response_text = f"❌ Task not found: {args}"
        else:
            response_text = "⚠️ Task manager not initialized."

    elif command == CommandType.CANCEL:
        if not args:
            response_text = "⚠️ Please provide a task ID.\nUsage: /cancel <task_id>"
        elif manager:
            success = await manager.cancel_task(args)
            if success:
                response_text = f"✅ Task cancelled: {args}"
            else:
                response_text = f"⚠️ Could not cancel task (may not be running): {args}"
        else:
            response_text = "⚠️ Task manager not initialized."

    else:
        response_text = "Unknown command. Type /help for available commands."

    # Send response back to Telegram
    if response_text:
        await send_telegram_message(chat_id, response_text)

    return {"ok": True}


# Lazy bot instance — only created when first message is sent
_bot = None


def _get_bot():
    """Get or create the Telegram bot instance (singleton)."""
    global _bot
    if _bot is None:
        import os
        from telegram import Bot
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not token:
            raise RuntimeError(
                "TELEGRAM_BOT_TOKEN environment variable is not set. "
                "Please set it before sending messages."
            )
        _bot = Bot(token=token)
    return _bot


async def send_telegram_message(chat_id: int, text: str, parse_mode=None):
    """Send a message to Telegram using the Bot API."""
    try:
        bot = _get_bot()
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
        )
        logger.info(f"Telegram message sent to {chat_id}: {text[:80]!r}")
    except Exception as e:
        logger.exception(f"Failed to send Telegram message to {chat_id}: {e}")
