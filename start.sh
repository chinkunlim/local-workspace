#!/bin/bash

# --- 定義顏色 ---
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # 無顏色

# 獲取腳本所在目錄的絕對路徑
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${WORKSPACE_DIR}/logs"
mkdir -p "$LOG_DIR"

echo -e "${CYAN}==================================================${NC}"
echo -e "${CYAN}          🚀 Starting AI Ecosystem              ${NC}"
echo -e "${CYAN}==================================================${NC}"

# 自定義等待特定端口的函數 (智慧且動態的取代 sleep)
wait_for_port() {
    local port=$1
    local service=$2
    local max_retries=30
    local retry=0
    
    echo -ne "   ${YELLOW}Waiting for $service on port $port...${NC} "
    while ! nc -z localhost $port >/dev/null 2>&1; do
        sleep 1
        retry=$((retry+1))
        if [ $retry -ge $max_retries ]; then
            echo -e "\n   ${RED}❌ Timeout waiting for $service${NC}"
            return 1
        fi
    done
    echo -e "${GREEN}✅ Up${NC}"
}

# 1. Ollama
echo -ne "${YELLOW}[1/5] Checking Ollama...${NC} "
if ! pgrep -x 'ollama' > /dev/null && ! nc -z localhost 11434 >/dev/null 2>&1; then
    open -a Ollama
    wait_for_port 11434 "Ollama" || true
else
    echo -e "${BLUE}ℹ️ Already running${NC}"
fi

# 2. LiteLLM
echo -e "\n${YELLOW}[2/5] Starting LiteLLM (Port 4000)...${NC}"
if ! nc -z localhost 4000 >/dev/null 2>&1; then
    (
        cd "${WORKSPACE_DIR}/litellm" || exit
        source .venv/bin/activate
        # 啟動服務並縮排輸出到 Log
        .venv/bin/litellm --config "${WORKSPACE_DIR}/litellm-config.yaml" --port 4000 > "${LOG_DIR}/litellm.log" 2>&1 &
    )
    wait_for_port 4000 "LiteLLM"
else
    echo -e "   ${BLUE}─── ℹ️ LiteLLM already running${NC}"
fi

# 3. Open WebUI
echo -e "\n${YELLOW}[3/5] Starting Open WebUI (Port 8080)...${NC}"
if ! nc -z localhost 8080 >/dev/null 2>&1; then
    DATA_DIR="${WORKSPACE_DIR}/open-webui" uvx --python 3.11 open-webui@latest serve > "${LOG_DIR}/open-webui.log" 2>&1 &
    wait_for_port 8080 "Open WebUI"
else
    echo -e "   ${BLUE}─── ℹ️ Open WebUI already running${NC}"
fi

# 4. Pipelines
echo -e "\n${YELLOW}[4/5] Starting Pipelines (Port 9099)...${NC}"
if ! nc -z localhost 9099 >/dev/null 2>&1; then
    (
        cd "${WORKSPACE_DIR}/pipelines" || exit
        source .venv/bin/activate
        sh start.sh > "${LOG_DIR}/pipelines.log" 2>&1 &
    )
    wait_for_port 9099 "Pipelines"
else
    echo -e "   ${BLUE}─── ℹ️ Pipelines already running${NC}"
fi

# 5. Open Claw
echo -e "\n${YELLOW}[5/5] Checking Open Claw (Port 18789)...${NC}"
if ! nc -z localhost 18789 >/dev/null 2>&1; then
    openclaw gateway > "${LOG_DIR}/openclaw.log" 2>&1 &
    wait_for_port 18789 "Open Claw"
else
    echo -e "   ${BLUE}─── ℹ️ Open Claw is already running${NC}"
fi

# --- 最終狀態彙整表 ---
echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  🌐 SERVICE DASHBOARD${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
printf "  %-20s → ${GREEN}%s${NC}\n" "Open WebUI" "http://localhost:8080"
printf "  %-20s → ${GREEN}%s${NC}\n" "Ollama" "http://localhost:11434"
printf "  %-20s → ${GREEN}%s${NC}\n" "Gemini Gate" "http://localhost:4000"
printf "  %-20s → ${GREEN}%s${NC}\n" "Pipelines" "http://localhost:9099"
printf "  %-20s → ${GREEN}%s${NC}\n" "Open Claw" "http://127.0.0.1:18789"
echo -e "  ${YELLOW}%-20s → open app → Start Server${NC}" "LM Studio"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# 自動開啟瀏覽器 (只確保 Open WebUI 真正在跑才打開)
if nc -z localhost 8080 >/dev/null 2>&1; then
    open http://localhost:8080
fi
