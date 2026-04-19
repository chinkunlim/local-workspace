# Open Claw 知識庫生態系：使用者手冊 (User Manual)

歡迎來到你的「個人 AI 第二大腦」！這套系統基於 Open Claw 架構，完全在你的本地機器運行，確保極致的隱私與客製化能力。

本手冊將帶你快速掌握如何將日常的學習素材（錄音、PDF、想法）轉化為結構化的知識，並透過 Obsidian 與 Telegram 隨時檢索與複習。

---

## 🚀 1. 系統啟動與關閉

在開始任何操作之前，請確保系統服務已啟動。

### 啟動系統
打開終端機，執行以下指令：
```bash
cd ~/Desktop/local-workspace
./infra/scripts/start.sh
```
啟動腳本會自動為你：
1. 開啟防休眠模式 (`caffeinate`)，保護長時間運算。
2. 啟動 Ollama、LiteLLM 與 Pipelines。
3. 啟動 Open Claw 總管與高專注力 Web App。
4. 啟動 `inbox_daemon` 24 小時監控收件匣。

### 關閉系統
當你結束工作時，請優雅地關閉系統以釋放記憶體與連接埠：
```bash
./infra/scripts/stop.sh
```

---

## 🌊 2. 核心觀念：知識流動的三個階段

不要去翻找複雜的程式目錄，你只需要記住這三個地方：

1. **📥 唯一入口 (Universal Inbox)**：`open-claw-sandbox/data/raw/`
   這是你唯一需要手動放檔案的地方。
2. **🏭 隱形工廠 (Factory Floors)**：`data/audio-transcriber/` 與 `data/doc-parser/`
   系統在背景自動運作的處理區，產生各種半成品。**你不需要管這裡**。
3. **🧠 終極大腦 (The Storefront)**：`open-claw-sandbox/data/wiki/`
   所有處理好的、打上雙向連結的精華筆記都在這裡。這也是你的 **Obsidian Vault**。

---

## 📝 3. 日常操作指南

### 情境 A：我上完課錄了音，或是下載了一份 PDF 論文，該怎麼辦？
1. 將你的 `.m4a` 錄音檔或 `.pdf` 文件，直接拖曳到 `open-claw-sandbox/data/raw/` 資料夾中。
2. 系統的 `inbox_daemon` 會自動偵測到檔案，把它分發到對應的工廠。
3. 系統會在背景默默地幫你進行轉錄、校對、畫重點、總結合成本。
4. 完成後，`knowledge-compiler` 會自動把它發布到你的 Obsidian (`data/wiki/`) 裡。

### 情境 B：我想閱讀、複習已經整理好的知識
1. 下載並安裝 [Obsidian](https://obsidian.md/)。
2. 打開 Obsidian，點擊 **「開啟資料夾作為 Vault (Open folder as vault)」**。
3. 選擇路徑：`~/Desktop/local-workspace/open-claw-sandbox/data/wiki/`。
4. 你會看到所有完美的 Markdown 筆記，並且可以直接打開「Graph view (關聯圖)」欣賞你的知識星系。

### 情境 C：我在 Obsidian 讀筆記時，突然有看不懂的地方
這套系統支援 **「互動式閱讀 (Interactive Reader)」**！
1. 直接在 Obsidian 的筆記段落下方，打上這樣的指令：
   ```markdown
   > [AI: 請用小學生的口吻解釋上一段提到的神經可塑性]
   ```
2. 存檔後，系統會在背景偵測到這個標籤，並將 AI 的回答直接「原地寫回」這份筆記中！

---

## 🤖 4. 如何向你的「大腦」提問？

當知識庫建立起來後，你可以隨時隨地向它發問。我們提供了兩種主要介面：

### 介面一：Telegram (行動客服模式)
如果你在外出時突然想到一個問題，直接打開你的 Telegram 傳送訊息給你的 Bot：
*   **問答 (RAG)**：「請問我的筆記裡有沒有提到費曼學習法？」
    *(系統會自動去 ChromaDB 撈出你的筆記並回答你)*
*   **學術比對**：「請比較行為主義與認知心理學」
    *(系統會調動 `academic-edu-assistant` 進行交叉比對，並產出報告與 Anki 卡片)*
*   **傳送檔案**：你也可以直接把錄音檔或 PDF 傳給機器人，它會自動丟進 Inbox！

### 介面二：Web App (高專注沉浸模式)
當你在電腦前，想要不受打擾地與知識庫對話：
1. 打開瀏覽器，輸入 `http://localhost:5001`。
2. 你會看到一個極簡、深色毛玻璃風格的畫面。
3. 在正中央的巨大輸入框輸入你的問題，點擊「詢問知識庫」或「交叉比對」即可獲得沉浸式的解答。

---

## 🛠️ 5. 系統技能 (Skills) 總覽與進階指令

如果你想手動觸發某些技能，可以進入 `open-claw-sandbox/` 目錄並使用 CLI 指令：

| 技能名稱 | 說明 | CLI 手動觸發指令 |
| :--- | :--- | :--- |
| **audio-transcriber** | 將語音轉為結構化筆記 | `python skills/audio-transcriber/scripts/run_all.py` |
| **doc-parser** | 將 PDF 轉為結構化筆記 | `python skills/doc-parser/scripts/run_all.py` |
| **knowledge-compiler** | 編譯大腦星系圖 | `python skills/knowledge-compiler/scripts/run_all.py` |
| **interactive-reader** | 處理 Markdown 裡的 AI 指令 | `python skills/interactive-reader/scripts/run_all.py` |
| **telegram-kb-agent** | 重建向量索引庫 | `python skills/telegram-kb-agent/scripts/indexer.py` |
| **academic-edu-assistant** | 手動執行交叉比對 | `python skills/academic-edu-assistant/scripts/run_all.py --query "你的查詢"` |

> 💡 **提示**：所有的 CLI 指令都支援 `--force` 參數來強制重新執行，或是 `--subject "科目名"` 來指定單一科目。

享受你的第二大腦吧！🚀
