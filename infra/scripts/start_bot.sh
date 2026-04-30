#!/bin/bash
# start_bot.sh - 獨立啟動 Telegram Bot (全能遙控中樞)

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

script_dir="$( cd "$( dirname "$0" )" && pwd )"
if [ "$script_dir" = "/" ] || [ -z "$script_dir" ] || [ "$script_dir" = "." ]; then
    script_dir="$PWD"
fi
INFRA_DIR="$(dirname "$script_dir")"
_LOCAL_WORKSPACE="$(dirname "$INFRA_DIR")"
WORKSPACE_DIR="${_LOCAL_WORKSPACE}/open-claw-sandbox"

export WORKSPACE_DIR
export PATH="/opt/homebrew/bin:/usr/local/bin:${PATH}"
export PYTHONPATH="${_LOCAL_WORKSPACE}:${WORKSPACE_DIR}:${PYTHONPATH}"

LOG_DIR="${WORKSPACE_DIR}/logs"
mkdir -p "$LOG_DIR"
BOT_DAEMON_PID_FILE="${LOG_DIR}/bot_daemon.pid"

echo -e "${YELLOW}Starting Telegram Bot Daemon (Standalone)...${NC}"
if [[ -f "${BOT_DAEMON_PID_FILE}" ]] && kill -0 "$(cat "${BOT_DAEMON_PID_FILE}")" 2>/dev/null; then
    echo -e "   ${BLUE}─── ℹ️ Bot Daemon already running (PID: $(cat "${BOT_DAEMON_PID_FILE}"))${NC}"
else
    (
        cd "${WORKSPACE_DIR}" || exit
        python3 skills/telegram_kb_agent/scripts/bot_daemon.py > "${LOG_DIR}/bot_daemon.log" 2>&1 &
        echo $! > "${BOT_DAEMON_PID_FILE}"
    )
    sleep 1
    echo -e "   ${GREEN}✓ Bot Daemon started (PID: $(cat "${BOT_DAEMON_PID_FILE}"))${NC}"
fi
