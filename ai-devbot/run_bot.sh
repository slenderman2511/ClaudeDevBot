#!/bin/bash

# AI DevBot - Helper Script
# Usage: ./run_bot.sh [command]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load .env file if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Add Claude CLI to PATH
export PATH="$HOME/.local/bin:$PATH"

# Unset CLAUDECODE to allow nested Claude sessions
unset CLAUDECODE

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

show_help() {
    echo -e "${GREEN}AI DevBot Helper${NC}"
    echo ""
    echo "Usage: ./run_bot.sh [command]"
    echo ""
    echo "Commands:"
    echo "  start     Start the Telegram bot"
    echo "  stop      Stop the Telegram bot"
    echo "  restart   Restart the Telegram bot"
    echo "  status    Check if bot is running"
    echo "  help      Show this help message"
    echo ""
}

start_bot() {
    if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
        echo -e "${YELLOW}Error: TELEGRAM_BOT_TOKEN not set in .env file${NC}"
        exit 1
    fi
    echo "Starting AI DevBot..."
    TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN" python3 -m bot.telegram_bot &
    echo "Bot started!"
}

stop_bot() {
    echo "Stopping AI DevBot..."
    pkill -f "bot.telegram_bot" 2>/dev/null
    echo "Bot stopped!"
}

check_status() {
    if pgrep -f "bot.telegram_bot" > /dev/null; then
        echo -e "${GREEN}Bot is running${NC}"
    else
        echo -e "${YELLOW}Bot is not running${NC}"
    fi
}

# Main
case "${1:-help}" in
    start)
        start_bot
        ;;
    stop)
        stop_bot
        ;;
    restart)
        stop_bot
        sleep 1
        start_bot
        ;;
    status)
        check_status
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${YELLOW}Unknown command: $1${NC}"
        show_help
        ;;
esac
