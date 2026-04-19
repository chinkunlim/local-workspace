# Open Claw 知識庫生態系：完整使用者手冊 (User Manual)

歡迎來到你的「個人 AI 第二大腦」！這套系統基於 Open Claw 架構，完全在你的本地機器運行，確保極致的隱私與客製化能力。

本手冊將帶你詳細了解如何將日常的學習素材（錄音、PDF、想法）轉化為結構化的知識，並透過 Obsidian 與 Telegram 隨時檢索與複習。

---

## 🚀 1. 系統啟動與關閉

在開始任何操作之前，請確保底層基礎設施（如 Ollama, Open Claw API 等）已啟動。

### 啟動基礎服務
打開終端機，執行以下指令：
```bash
cd ~/Desktop/local-workspace
./infra/scripts/start.sh
```
啟動腳本會自動為你：
1. 開啟防休眠模式 (`caffeinate`)，保護長時間運算。
2. 啟動 Ollama、LiteLLM 與 Pipelines。
3. 啟動 Open Claw API Gateway。
4. 啟動 `inbox_daemon` 24 小時監控收件匣。

### 關閉基礎服務
當你結束工作時，請優雅地關閉系統以釋放記憶體與資源：
```bash
./infra/scripts/stop.sh
```

---

## 🌊 2. 核心觀念：知識流動的三個階段

本生態系將資料的處理分為三個明確的區域。你只需理解這三個區域，就能輕鬆掌控整套系統。

### 📥 階段一：唯一收發室 (Universal Inbox)
*   **路徑**：`open-claw-sandbox/data/raw/`
*   **用途**：這是你**唯一需要手動放入檔案**的地方。不管是錄音檔 (`.m4a`)、PDF 論文，只要想處理，就全部丟進來。
*   **自動化**：背景的 `inbox_daemon` 會自動偵測檔案，把它們分發到正確的「隱形工廠」進行處理。

### 🏭 階段二：隱形工廠 (Factory Floors)
*   **路徑**：`data/audio-transcriber/` 與 `data/doc-parser/` 等。
*   **用途**：系統在背景自動運作的處理區。檔案會經歷 P1(初稿) -> P2(校對) -> P3(合成) 等階段。
*   **注意**：這裡充滿了半成品，**你完全不需要（也不應該）去管理這裡的檔案**。

### 🧠 階段三：終極大腦展示區 (The Storefront / Obsidian)
*   **路徑**：`open-claw-sandbox/data/wiki/`
*   **用途**：所有處理好的、打上雙向連結的精華筆記都在這裡。這也是你的 **Obsidian Vault**。所有的知識閱讀、編輯、以及二次加工，都是基於這個資料夾。

---

## 📝 3. 核心情境與操作指南

### 情境 A：我上完課錄了音，或是下載了一份 PDF，該怎麼處理？
1. 將你的 `.m4a` 或 `.pdf` 檔案，直接拖曳到 `data/raw/` 資料夾中。
2. 就這樣！系統會自動開始在背景進行處理。
3. 如果你想查看進度，可以打開 Open Claw 的操作介面，它會顯示各個管線的執行狀態。

### 情境 B：我想閱讀、複習已經整理好的知識
1. 下載並安裝 [Obsidian](https://obsidian.md/)。
2. 打開 Obsidian，選擇 **「開啟資料夾作為 Vault (Open folder as vault)」**。
3. 選擇路徑：`~/Desktop/local-workspace/open-claw-sandbox/data/wiki/`。
4. 你會看到所有完美的 Markdown 筆記。點擊右側的「Graph view (關聯圖)」，即可欣賞你的知識星系圖。

### 情境 C：我在 Obsidian 讀筆記時，突然有看不懂的地方
本系統內建 **「互動式閱讀 (Interactive Reader)」** 功能，讓筆記活起來！
1. 在 Obsidian 筆記中，直接在你看不懂的段落下方，打上這樣的指令：
   ```markdown
   > [AI: 請用小學生的口吻解釋上一段提到的神經可塑性]
   ```
2. 存檔後，透過 Open Claw 執行 `interactive-reader` 技能，系統會將 AI 的回答直接「原地寫回」這份筆記中！

---

## 🤖 4. 行動端與進階提問 (Open Claw & Telegram)

我們已經將所有功能整合為 Open Claw 的原生技能 (Native Skills)。

### 透過 Open Claw 介面
因為所有的模組都已經配備了 `SKILL.md`，如果你打開 Open Claw 的介面，你將會看到以下技能可供點擊或調度：
*   **`audio-transcriber`**：語音轉文字管線。
*   **`doc-parser`**：PDF 文件解析管線。
*   **`knowledge-compiler`**：編譯大腦星系圖（將工廠的產出打包到 `wiki/`）。
*   **`academic-edu-assistant`**：交叉比對學術理論。
*   **`telegram-kb-agent`**：對話式知識庫查詢 (RAG)。

### 透過 Telegram 機器人
當你在外通勤時，你可以透過 Telegram 傳送訊息給 Open Claw。因為 Open Claw 具有意圖識別能力，它會在背景自動幫你調度對應的 Python 腳本：
*   **詢問知識 (RAG)**：傳送「請問我的筆記裡有沒有提到費曼學習法？」，Open Claw 會調度 `telegram-kb-agent` 回答你。
*   **交叉比對**：傳送「請比較行為主義與認知心理學」，Open Claw 會調度 `academic-edu-assistant` 產出報告。
*   **收件**：直接把檔案傳給機器人，它會自動幫你放進 `data/raw/` 觸發管線！

---

## ❓ 常見問題 (FAQ)

### Q1: 為什麼程式碼裡有些地方提到 "Notion Synthesis"，但我找不到同步到 Notion 的功能？
在早期的架構中，我們確實嘗試過透過 API 直接同步到 Notion。但後來我們決定轉向 **「本地優先 (Local-first)」** 的架構，因為 Notion 需要依賴雲端與 API Token，這與我們追求極致隱私與離線可用性的目標相衝突。

因此，現在的 `05_notion_synthesis.py` 產出的其實是 **「完美相容於 Obsidian 的 Markdown 筆記」**，並統一存放在 `data/wiki/` 裡。
*(如果你依然非常想用 Notion，你完全可以直接將 `data/wiki/` 這個資料夾匯入到你的 Notion 中！)*

### Q2: `note-generator` (筆記生成器) 要怎麼單獨使用？
`note-generator` 是一個「二次加工」模組。它目前已經內建在 `audio-transcriber` 和 `doc-parser` 的最後一個步驟中。也就是說，系統自動產出的筆記，就已經是經過 `note-generator` 精煉與生成 Mermaid 心智圖的版本了。未來你可以透過 Open Claw 介面，傳入任何一段純文字讓它幫你生成筆記。
