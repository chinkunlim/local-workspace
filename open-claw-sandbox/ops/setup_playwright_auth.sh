#!/bin/bash

# --- 定義顏色 ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

script_dir="$( cd "$( dirname "$0" )" && pwd )"
WORKSPACE_DIR="$(dirname "$script_dir")"
PROFILE_DIR="${WORKSPACE_DIR}/data/playwright_profile"

echo -e "${CYAN}==================================================${NC}"
echo -e "${CYAN}      🛡️ Playwright Persistent Auth Setup       ${NC}"
echo -e "${CYAN}==================================================${NC}"
echo -e "${YELLOW}此腳本將開啟兩個 Chrome 視窗，請在視窗中完成以下登入：${NC}"
echo "1. 登入 Google 帳號 (Gemini)"
echo "2. 登入東華大學 OpenAthens (ScienceDirect / Elsevier)"
echo "登入完成後，請直接關閉瀏覽器視窗，登入狀態將永久保存供 Agent 使用。"
echo ""
read -p "按下 Enter 鍵開始啟動瀏覽器..."

mkdir -p "$PROFILE_DIR"

echo -e "\n${GREEN}[1/2] 開啟 Google Gemini...${NC}"
echo "請在跳出的視窗中完成 Google 帳號登入，成功進入 Gemini 聊天介面後，關閉視窗。"
playwright open --user-data-dir="$PROFILE_DIR" --channel="chrome" "https://gemini.google.com"

echo -e "\n${GREEN}[2/2] 開啟 ScienceDirect (東華大學登入)...${NC}"
echo "請在跳出的視窗中，選擇透過機構登入 (Institution Login)，並輸入東華大學 Athens 帳密。登入成功後，關閉視窗。"
playwright open --user-data-dir="$PROFILE_DIR" --channel="chrome" "https://www.sciencedirect.com/"

echo -e "\n${CYAN}==================================================${NC}"
echo -e "${GREEN}✅ 認證狀態已成功保存至: ${PROFILE_DIR}${NC}"
echo -e "${CYAN}==================================================${NC}"
