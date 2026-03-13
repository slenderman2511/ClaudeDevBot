# telegram_claude_bot.py
import os
import subprocess
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Load token from environment variable
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN not set!")
    print("Set it with: export TELEGRAM_BOT_TOKEN='your_token'")
    exit(1)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    # Call Claude Code CLI
    result = subprocess.run(
        ["claude", "-p", user_message],
        capture_output=True,
        text=True,
        input=user_message
    )

    response = result.stdout or result.stderr
    await update.message.reply_text(response[:4000])  # Telegram limit


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! Send me a message and I'll forward it to Claude Code.")


app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start_command))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.run_polling(pending_write_timeout=300)
