# AI Ecosystem Workspace Structure

> This outlines the global layout of `local-workspace`, which sits above the `open-claw-workspace` sandbox.

```
/Users/limchinkun/Desktop/local-workspace
├── .claude_profile.md          # 🧠 [全局大腦] 定義硬體環境、AI 開發習慣與溝通規則
├── cline-provider.md           # 📖 [速查表] 記錄 VS Code Cline 切換 Ollama/Gemini 的設定參數
├── litellm-config.yaml         # 🔀 [路由設定] LiteLLM 的配置檔，包含 Gemini API keys 與負載均衡規則
├── start.sh                    # 🚀 [一鍵啟動] 啟動 Ollama、LiteLLM、Open WebUI、Pipelines 與 Open Claw
├── stop.sh                     # 🛑 [一鍵停止] 乾淨地關閉所有背景服務、殺死 9099 端口並釋放 RAM
└── watchdog.sh                 # 👁️ [系統守衛] 背景監控 RAM，低於 1.5GB 自動剔除 Ollama 模型防當機

├── backups/                    # 📦 [備份區] 備份與歷史檔案、測試腳本
│   ├── Gemini_Cost_Guard.py    # [歷史備份] API 額度守衛的原始開發草稿 (最終運作版已移至 pipelines/pipelines/ 內)
│   ├── RAM_Safety_Guard.py     # [歷史備份] 記憶體安全守衛的原始開發草稿 (最終運作版已移至 pipelines/pipelines/ 內)
│   └── generate_tree.py        # [實用工具] 用來掃描整個 local-workspace 目錄並自動生成結構樹狀圖的 Python 腳本

├── litellm/                    # 🔷 [API 網關] LiteLLM 虛擬環境與密鑰
│   └── .webui_secret_key

├── logs/                       # 📋 [日誌區] 系統運行日誌 (排錯時看這裡)
│   └── workspace_structure.md  # 包含本說明的目錄樹狀解說檔

├── manual/                     # 📚 [操作手冊] 歷史說明文件
│   └── (各種 DOCX 文件)

├── modelfiles/                 # 🦙 [Ollama 模型] 自訂模型的 System Prompts 藍圖
│   ├── Modelfile-chinese       # (gemma-chinese) 負責中文文件翻譯與學術整理
│   ├── Modelfile-coder         # (qwen-coder) 日常寫扣主力
│   ├── Modelfile-multi         # (qwen-multi) 多語言對話
│   ├── Modelfile-night         # (deepseek-night) 夜間批次運行的重型模型
│   └── Modelfile-reason        # (deepseek-reason) 邏輯推理與數學

├── open-claw-workspace/        # 🦞 [Open Claw 沙盒] Agent 專屬工作區 (與實體機隔離)
│   ├── AGENTS.md               # 系統自動生成的 Agent 設定檔
│   ├── BOOTSTRAP.md            # 從 0 啟動的說明指南
│   ├── ...                     # 詳見 open-claw-workspace/docs/STRUCTURE.md
│   └── docs/
│       └── STRUCTURE.md        # Open Claw 內部檔案架構

├── open-webui/                 # 🌐 [WebUI 前端] DATA_DIR 資料庫與快取
│   ├── webui.db                # [核心資料庫] 儲存聊天紀錄、提示詞與帳號
│   ├── vector_db/              # [RAG 向量庫] 上傳文件的向量化數據
│   └── cache/                  # [快取區]

├── pipelines/                  # 🔌 [管線伺服器] Port 9099 的獨立擴展系統
│   ├── start.sh                # 正式啟動腳本
│   ├── main.py                 # 伺服器主程式
│   └── pipelines/              # 🚨 [自訂管線] 你的腳本實體存放處
│       ├── Gemini_Cost_Guard.py  # API 額度守衛腳本
│       └── RAM_Safety_Guard.py   # 記憶體安全守衛腳本

└── project_dev/                # 🛠️ [開發工作區] 專案的實際產出地點
    ├── projectName1/           # [專案] 農業價格追蹤系統
    └── projectName2/           # [專案] 穿戴式裝置與數位寵物系統
```
