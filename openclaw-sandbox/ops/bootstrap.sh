#!/usr/bin/env bash
# Open Claw Workspace - macOS Bootstrap Script
set -euo pipefail

# 設定 WORKSPACE_DIR 環境變數
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export WORKSPACE_DIR
export PYTHONPATH="${WORKSPACE_DIR}:${WORKSPACE_DIR}/openclaw-sandbox:${PYTHONPATH}"

echo "🔧 正在驗證 Open Claw Workspace 相依環境..."
echo "   WORKSPACE_DIR: $WORKSPACE_DIR"
echo "   PYTHONPATH: $PYTHONPATH"

# 1. 檢查 Homebrew
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
if ! command -v brew &> /dev/null
then
    echo "❌ 找不到 Homebrew。請先安裝 Homebrew: https://brew.sh"
    exit 1
fi

# 2. 安裝系統級套件
echo "📦 正在檢查與安裝系統套件 (poppler, tesseract)..."
brew list poppler &>/dev/null || brew install poppler
brew list tesseract &>/dev/null || brew install tesseract
brew list tesseract-lang &>/dev/null || brew install tesseract-lang

# 3. 安裝 Python 套件
echo "🐍 正在安裝 Python 套件..."
pip3 install -r "${WORKSPACE_DIR}/requirements.txt"

# 4. 初始化 Playwright 瀏覽器 (如果 playwright 已安裝)
if command -v playwright &> /dev/null; then
    echo "🌐 正在初始化 Playwright..."
    playwright install chromium
fi

echo "✅ 環境配置完成！您現在可以正常啟動 Audio Transcriber 與 Doc Parser 技能了。"
