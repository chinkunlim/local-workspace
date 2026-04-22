#!/bin/bash
# install_bot_service.sh - 設定 Telegram Bot 在 Mac 開機時自動在背景執行

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

script_dir="$( cd "$( dirname "$0" )" && pwd )"
if [ "$script_dir" = "/" ] || [ -z "$script_dir" ] || [ "$script_dir" = "." ]; then
    script_dir="$PWD"
fi

PLIST_PATH="$HOME/Library/LaunchAgents/com.openclaw.telegrambot.plist"
START_BOT_SH="$script_dir/start_bot.sh"

echo -e "${YELLOW}設定 Telegram Bot 背景常駐服務...${NC}"

cat <<EOF > "$PLIST_PATH"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.openclaw.telegrambot</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$START_BOT_SH</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>StandardOutPath</key>
    <string>$HOME/Library/Logs/openclaw_bot.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/Library/Logs/openclaw_bot_error.log</string>
</dict>
</plist>
EOF

# 卸載舊的設定 (如果存在)
launchctl unload "$PLIST_PATH" 2>/dev/null

# 載入新的設定
launchctl load "$PLIST_PATH"

echo -e "${GREEN}✅ Telegram Bot 已設定為開機自動執行！${NC}"
echo -e "你可以隨時使用這兩個腳本手動控制它："
echo -e "啟動: $script_dir/start_bot.sh"
echo -e "停止: $script_dir/stop_bot.sh"
