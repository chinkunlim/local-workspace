#!/bin/bash
# stop_bot.sh - 停止獨立的 Telegram Bot

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

script_dir="$( cd "$( dirname "$0" )" && pwd )"
if [ "$script_dir" = "/" ] || [ -z "$script_dir" ] || [ "$script_dir" = "." ]; then
    script_dir="$PWD"
fi
INFRA_DIR="$(dirname "$script_dir")"
_LOCAL_WORKSPACE="$(dirname "$INFRA_DIR")"
WORKSPACE_DIR="${_LOCAL_WORKSPACE}/openclaw-sandbox"
LOG_DIR="${WORKSPACE_DIR}/logs"
BOT_DAEMON_PID_FILE="${LOG_DIR}/bot_daemon.pid"

echo -e "${YELLOW}Stopping Telegram Bot Daemon...${NC}"
if [[ -f "${BOT_DAEMON_PID_FILE}" ]]; then
    kill -15 "$(cat "${BOT_DAEMON_PID_FILE}")" 2>/dev/null
    rm -f "${BOT_DAEMON_PID_FILE}"
    echo -e "   ${GREEN}✓ Bot Daemon stopped${NC}"
else
    echo -e "   ${GREEN}✓ Bot Daemon is not running${NC}"
fi
