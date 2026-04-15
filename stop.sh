#!/bin/bash

# --- 定義顏色 ---
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # 無顏色

echo -e "${CYAN}==================================================${NC}"
echo -e "${CYAN}          🛑 Stopping AI Ecosystem              ${NC}"
echo -e "${CYAN}==================================================${NC}"

# 安全清理特定埠口的函數 (優雅中止，避免資料庫損毀)
kill_by_port() {
    local port=$1
    local name=$2
    local pids
    pids=$(lsof -ti:$port 2>/dev/null)
    
    if [ ! -z "$pids" ]; then
        echo -ne "   ${YELLOW}Stopping $name (Port $port)...${NC} "
        # 嘗試 SIGTERM 優雅關閉
        echo "$pids" | xargs kill -15 2>/dev/null
        sleep 2
        
        # 檢查是否已關閉，若無則強制結束 SIGKILL
        pids=$(lsof -ti:$port 2>/dev/null)
        if [ ! -z "$pids" ]; then
            echo "$pids" | xargs kill -9 2>/dev/null
        fi
        echo -e "${GREEN}✅ Stopped${NC}"
    else
        echo -e "   ${BLUE}ℹ️ $name (Port $port) is not running${NC}"
    fi
}

# 1. Open Claw
echo -e "${YELLOW}[1/3] Terminating Open Claw...${NC}"
if lsof -ti:18789 > /dev/null 2>&1; then
    openclaw gateway stop > /dev/null 2>&1 || true
    kill_by_port 18789 "Open Claw"
else
    echo -e "   ${BLUE}─── ℹ️ Open Claw is not running${NC}"
fi

# 2. Python Services & Port Cleaning
echo -e "\n${YELLOW}[2/3] Cleaning up Python services & Ports...${NC}"
kill_by_port 4000 "LiteLLM"
kill_by_port 8080 "Open WebUI"
kill_by_port 9099 "Pipelines"

# 清理可能的孤兒程序 (安全檢查)
pkill -f "python3.*pipelines/start.sh" 2>/dev/null || true

# 3. Ollama
echo -e "\n${YELLOW}[3/3] Unloading Ollama models & app...${NC}"
if nc -z localhost 11434 >/dev/null 2>&1 || pgrep -x "ollama" > /dev/null; then
    # 卸載正在跑的模型以釋放顯存
    active_models=$(ollama ps 2>/dev/null | awk 'NR>1 {print $1}')
    if [ ! -z "$active_models" ]; then
        for model in $active_models; do
            ollama stop $model >/dev/null 2>&1 || true
        done
        echo -e "   ${GREEN}─── ✅ Ollama models unloaded${NC}"
    fi

    # 使用 Mac 原生方式優雅關閉 Ollama 應用，避免強殺導致的錯誤
    if osascript -e 'id of application "Ollama"' >/dev/null 2>&1; then
        osascript -e 'quit app "Ollama"' >/dev/null 2>&1
        echo -e "   ${GREEN}─── ✅ Ollama app quit gracefully${NC}"
    else
        pkill -f "ollama" 2>/dev/null || true
        echo -e "   ${GREEN}─── ✅ Ollama processes killed${NC}"
    fi
else
    echo -e "   ${BLUE}─── ℹ️ Ollama was not running${NC}"
fi

# --- 最終狀態彙整 ---
echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  ✨ ALL SERVICES STOPPED${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 動態檢驗，而不是直接打 OFF
check_status() {
    if nc -z localhost $1 >/dev/null 2>&1; then
        echo -e "  ${RED}●${NC} $2 ($1): ${YELLOW}Still running!${NC}"
    else
        echo -e "  ${GREEN}●${NC} $2 ($1): ${GREEN}OFF${NC}"
    fi
}

check_status 4000  "LiteLLM   "
check_status 8080  "Open WebUI"
check_status 9099  "Pipelines "
check_status 18789 "Open Claw "

if nc -z localhost 11434 >/dev/null 2>&1 || pgrep -x "ollama" >/dev/null; then
    echo -e "  ${RED}●${NC} Ollama            : ${YELLOW}Still running!${NC}"
else
    echo -e "  ${GREEN}●${NC} Ollama            : ${GREEN}OFF${NC}"
fi
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
