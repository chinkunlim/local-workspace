# Open Claw 知識庫生態系：完整使用者手冊

歡迎來到你的「個人 AI 第二大腦」！這套系統完全在你的本地機器運行，確保極致的隱私與客製化能力。

本手冊分為兩部分：**[Part 1] 日常使用概念** 與 **[Part 2] 完整 CLI 操作教程**。

---

# Part 1：日常使用概念

## 🚀 1. 系統啟動與關閉

```bash
cd ~/Desktop/local-workspace

# 啟動所有服務
./infra/scripts/start.sh

# 關閉所有服務
./infra/scripts/stop.sh
```

啟動腳本會自動：
1. 開啟防休眠模式 (`caffeinate`)，保護長時間運算。
2. 啟動 Ollama、LiteLLM 與 Pipelines。
3. 啟動 Open Claw API Gateway（Port 18789）。
4. 啟動 `inbox_daemon` 24 小時監控收件匣。

---

## 🌊 2. 核心觀念：知識流動的三個階段

```
你的檔案
    │
    ▼
📥 data/raw/<科目>/          ← 唯一手動放入點
    │ inbox_daemon 自動分發
    ├──► 🏭 data/audio-transcriber/   (語音工廠)
    └──► 🏭 data/doc-parser/          (PDF 工廠)
                │
                ▼ 自動產出
    🧠 data/wiki/<科目>/               ← Obsidian Vault（最終成果）
```

### 📥 階段一：唯一收發室 (Universal Inbox)
- **路徑**：`open-claw-sandbox/data/raw/<科目名稱>/`
- **用途**：這是你**唯一需要手動放入檔案**的地方。
- **規則**：建立以科目命名的子資料夾，例如 `data/raw/認知心理學/`。

### 🏭 階段二：隱形工廠 (Factory Floors)
- **路徑**：`data/audio-transcriber/` 與 `data/doc-parser/`
- **用途**：系統在背景自動運作的處理區，你**不需要管理這裡的任何檔案**。

### 🧠 階段三：Obsidian Vault (The Brain)
- **路徑**：`open-claw-sandbox/data/wiki/`
- **用途**：所有精華 Markdown 筆記的最終歸宿，也是你的 Obsidian Vault。

---

## 📄 3. PDF 後綴路由規則

`inbox_daemon` 根據 PDF 檔名後綴自動判斷處理方式，規則定義在 `core/inbox_config.json`：

| 後綴範例 | 路由模式 | 說明 |
|---|---|---|
| `L1_slides.pdf`、`L1_ref.pdf`、`L1_handout.pdf` | `audio_ref` | 僅作為語音校對的參考，**不**獨立生成筆記 |
| `genetics_textbook.pdf`、`ch3_reading.pdf` | `both` | **同時**送去 doc-parser 解析 + 作為語音參考 |
| 不符合任何後綴 | `doc_parser` | 預設行為：送去 doc-parser 獨立解析 |

**完整後綴清單（`audio_ref` 模式）**：
`_ref`, `_refs`, `_slides`, `_slide`, `_handout`, `_handouts`, `_lecturenotes`, `_transcript`, `_worksheet`, `_supplement`, `_appendix`, `_coursework`, 以及中文關鍵字：`課件`, `講義`, `參考`

**完整後綴清單（`both` 模式）**：
`_textbook`, `_book`, `_chapter`, `_ch`, `_reading`, `_readings`, `_material`, `_materials`, `_guide`, `_notes`

---

## 🤖 4. 行動端與進階提問 (Open Claw & Telegram)

### 透過 Open Claw 介面
因為所有的模組都已配備 `SKILL.md`，你可以在 Open Claw 中直接用自然語言調度技能：
- **「幫我處理語音」** → 自動調度 `audio-transcriber`
- **「解析這份 PDF」** → 自動調度 `doc-parser`
- **「幫我對認知心理學的筆記生成總結」** → 調度 `note_generator`

### 透過 Telegram 機器人
- **詢問知識 (RAG)**：「請問我的筆記裡有沒有提到費曼學習法？」
- **交叉比對**：「請比較行為主義與認知心理學」
- **直接傳送檔案**：機器人會自動幫你放進 `data/raw/` 觸發管線

---

## 🔄 5. 全鏈路操作範例 (Obsidian ➡️ CLI ➡️ Open WebUI)

Open Claw 的設計哲學是讓各種介面無縫協作，以下是標準的跨介面工作流：

1. **觸發 (Obsidian)**：你在 Obsidian 中閱讀 `data/wiki/認知心理學/lecture_01.md` 時，覺得這篇筆記需要重新總結。你在 YAML frontmatter 加上 `status: rewrite`，並存檔。
2. **自動化 (CLI 背景執行)**：`inbox_daemon` 瞬間偵測到變化，自動在背景觸發 `note_generator` 重新合成該筆記，過程中會有 macOS **原生系統通知 (osascript)** 告訴你「Pipeline 啟動」與「執行完畢」。
3. **高階分析 (Open WebUI)**：筆記更新後，你打開 `http://localhost:8080` (Open WebUI)，在對話框中輸入「請基於我最新的認知心理學筆記，出一份測驗卷」，AI 將調用 RAG 讀取剛更新的內容並與你互動。

---

# Part 2：完整 CLI 操作教程

> **前提**：所有指令都在 `~/Desktop/local-workspace/open-claw-sandbox/` 目錄下執行。

```bash
cd ~/Desktop/local-workspace/open-claw-sandbox
```

---

## 🎙️ CLI-1：語音轉錄管線 (`audio-transcriber`)

**完整指令格式**：
```bash
python3 skills/audio-transcriber/scripts/run_all.py [選項]
```

### 基本使用

```bash
# 處理所有科目的所有語音檔（全量處理）
python3 skills/audio-transcriber/scripts/run_all.py

# 只處理指定科目
python3 skills/audio-transcriber/scripts/run_all.py --subject 認知心理學

# 只處理單一語音檔（精確操作）
python3 skills/audio-transcriber/scripts/run_all.py \
    --subject 認知心理學 \
    --file lecture_01-1.m4a \
    --single

# 強制重新處理（忽略已完成的進度記錄）
python3 skills/audio-transcriber/scripts/run_all.py --force
python3 skills/audio-transcriber/scripts/run_all.py --subject 認知心理學 --force
```

### 斷點續跑

```bash
# 如果上次處理到一半中斷，從 checkpoint 繼續
python3 skills/audio-transcriber/scripts/run_all.py --resume

# 從指定的 Phase 重新開始（例如從 Phase 2 校對重跑）
python3 skills/audio-transcriber/scripts/run_all.py --subject 認知心理學 --from 2
```

### 詞庫管理（提升校對準確率）

```bash
# 自動為指定科目生成專業術語詞庫
python3 skills/audio-transcriber/scripts/run_all.py --subject 認知心理學 --glossary

# 合併現有詞庫（補充新詞）
python3 skills/audio-transcriber/scripts/run_all.py --subject 認知心理學 --glossary-merge

# 強制重新生成詞庫（覆蓋舊版本）
python3 skills/audio-transcriber/scripts/run_all.py --subject 認知心理學 --glossary-force
```

### 互動審查模式

```bash
# 啟用人工分段確認（每個 Chunk 處理完後等你按 Enter）
python3 skills/audio-transcriber/scripts/run_all.py --subject 認知心理學 --interactive
```

### 常見工作流

```bash
# 工作流 A：標準流程（全自動，把 m4a 丟進 data/raw/ 後跑這個）
python3 skills/audio-transcriber/scripts/run_all.py --subject 認知心理學

# 工作流 B：重跑特定檔案的最後合成步驟
python3 skills/audio-transcriber/scripts/run_all.py \
    --subject 認知心理學 \
    --file lecture_01 \
    --single \
    --from 5

# 工作流 C：強制重做單一檔案的校對
python3 skills/audio-transcriber/scripts/run_all.py \
    --subject 認知心理學 \
    --file lecture_02 \
    --single \
    --from 2 \
    --force
```

---

## 📄 CLI-2：PDF 解析管線 (`doc-parser`)

**完整指令格式**：
```bash
python3 skills/doc-parser/scripts/run_all.py [選項]
```

### 基本使用

```bash
# 掃描收件匣，列出待處理的 PDF（不執行任何處理）
python3 skills/doc-parser/scripts/run_all.py --scan

# 處理下一個待辦 PDF
python3 skills/doc-parser/scripts/run_all.py --process-one

# 處理所有待辦 PDF（全量處理）
python3 skills/doc-parser/scripts/run_all.py --process-all

# 只處理指定科目
python3 skills/doc-parser/scripts/run_all.py --subject 認知心理學

# 只處理單一 PDF 檔案
python3 skills/doc-parser/scripts/run_all.py \
    --subject 認知心理學 \
    --file paper_attention.pdf \
    --single

# 強制重新處理
python3 skills/doc-parser/scripts/run_all.py --force --subject 認知心理學
```

### 斷點續跑

```bash
# 從上次中斷的地方繼續
python3 skills/doc-parser/scripts/run_all.py --resume --subject 認知心理學
```

### 互動審查模式

```bash
# 在 Phase 04（AI 解析）前啟用人工確認
python3 skills/doc-parser/scripts/run_all.py --subject 認知心理學 --interactive
```

### 常見工作流

```bash
# 工作流 A：標準流程（把 PDF 丟進 data/raw/ 後跑這個）
python3 skills/doc-parser/scripts/run_all.py --subject 認知心理學

# 工作流 B：先掃描再批量處理
python3 skills/doc-parser/scripts/run_all.py --scan
python3 skills/doc-parser/scripts/run_all.py --process-all

# 工作流 C：重跑單一 PDF 的知識合成
python3 skills/doc-parser/scripts/run_all.py \
    --subject 認知心理學 \
    --file textbook_ch3 \
    --single \
    --force
```

---

## 🧠 CLI-3：知識庫編譯 (`knowledge-compiler`)

把各個技能的輸出統一發布到 `data/wiki/`，建立雙向連結。

```bash
# 編譯所有科目
python3 skills/knowledge-compiler/scripts/run_all.py

# 只編譯指定科目
python3 skills/knowledge-compiler/scripts/run_all.py --subject 認知心理學

# 強制重新編譯所有科目
python3 skills/knowledge-compiler/scripts/run_all.py --force

# 編譯並只輸出單一檔案
python3 skills/knowledge-compiler/scripts/run_all.py \
    --subject 認知心理學 \
    --file lecture_01.md \
    --single
```

---

## ✏️ CLI-4：智慧重點標注 (`smart_highlighter`)

對任意 Markdown 文件進行 AI 重點標注（`==關鍵詞==` 格式）。

```bash
# 對單一 Markdown 文件進行重點標注
python3 skills/smart_highlighter/scripts/highlight.py \
    --input-file data/wiki/認知心理學/lecture_01.md \
    --output-file data/wiki/認知心理學/lecture_01_highlighted.md

# 指定科目上下文（讓 AI 知道這是哪個領域）
python3 skills/smart_highlighter/scripts/highlight.py \
    --subject 認知心理學 \
    --input-file data/wiki/認知心理學/lecture_01.md \
    --output-file data/wiki/認知心理學/lecture_01_highlighted.md

# 使用指定的模型 profile
python3 skills/smart_highlighter/scripts/highlight.py \
    --subject 認知心理學 \
    --profile default \
    --input-file data/wiki/認知心理學/lecture_01.md \
    --output-file data/wiki/認知心理學/lecture_01_highlighted.md
```

---

## 📝 CLI-5：筆記生成器 (`note_generator`)

對任意 Markdown 文件進行 Map-Reduce 式知識濃縮，生成結構化總結筆記與 Mermaid 心智圖。

```bash
# 對單一 Markdown 文件生成總結筆記
python3 skills/note_generator/scripts/synthesize.py \
    --input-file data/wiki/認知心理學/lecture_01.md \
    --output-file data/wiki/認知心理學/lecture_01_summary.md

# 指定科目與標籤（影響筆記的標題與上下文）
python3 skills/note_generator/scripts/synthesize.py \
    --subject 認知心理學 \
    --label "lecture_01" \
    --input-file data/wiki/認知心理學/lecture_01.md \
    --output-file data/wiki/認知心理學/lecture_01_summary.md

# 使用指定的模型 profile
python3 skills/note_generator/scripts/synthesize.py \
    --subject 認知心理學 \
    --label "lecture_01" \
    --profile default \
    --input-file data/wiki/認知心理學/lecture_01.md \
    --output-file data/wiki/認知心理學/lecture_01_summary.md
```

---

## 📋 CLI-6：收件匣路由規則管理 (`inbox-manager`)

動態管理 `core/inbox_config.json` 裡的 PDF 路由規則，**無需手動編輯 JSON**。

```bash
# 列出目前所有的路由規則
python3 skills/inbox-manager/scripts/query.py list

# 查看特定模式的規則（支援模糊搜索）
python3 skills/inbox-manager/scripts/query.py list | grep audio_ref
python3 skills/inbox-manager/scripts/query.py list | grep both
```

### 新增路由規則

```bash
# 新增 audio_ref 規則（檔名以 _ppt 結尾的 PDF → 僅作語音參考）
python3 skills/inbox-manager/scripts/query.py add \
    --add _ppt \
    --routing audio_ref \
    --description "PowerPoint 轉出的 PDF，僅作語音校對參考"

# 新增 both 規則（檔名含 _unit → 同時解析 + 語音參考）
python3 skills/inbox-manager/scripts/query.py add \
    --add _unit \
    --routing both \
    --description "教學單元 — 同時解析 & 供語音校對"

# 新增 doc_parser 規則（檔名含 _paper → 只走 doc-parser）
python3 skills/inbox-manager/scripts/query.py add \
    --add _paper \
    --routing doc_parser \
    --description "學術論文 — 完整解析轉成筆記"

# 新增中文關鍵字規則
python3 skills/inbox-manager/scripts/query.py add \
    --add 期末 \
    --routing both \
    --description "【繁中】期末考試相關材料"
```

### 刪除路由規則

```bash
# 刪除指定後綴的規則
python3 skills/inbox-manager/scripts/query.py remove --remove _ppt

# 刪除中文關鍵字規則
python3 skills/inbox-manager/scripts/query.py remove --remove 期末
```

---

## 📖 CLI-7：互動式閱讀器 (`interactive-reader`)

批次處理 `data/wiki/` 中含有 `> [AI: ...]` 標記的筆記，將 AI 的回答原地寫回。

```bash
# 處理所有科目的所有 AI 標記
python3 skills/interactive-reader/scripts/run_all.py

# 只處理指定科目
python3 skills/interactive-reader/scripts/run_all.py --subject 認知心理學
```

**使用方式**：在 Obsidian 筆記中加入以下標記，然後執行上述指令：
```markdown
> [AI: 請用一個生活中的例子解釋「工作記憶」]
```

---

## 🔬 CLI-8：學術比較助理 (`academic-edu-assistant`)

跨文件進行主題比較分析，並產出 Anki 卡片格式的複習素材。

```bash
# 執行跨文件比較分析（Phase 1）
python3 skills/academic-edu-assistant/scripts/run_all.py \
    --query "比較行為主義與認知主義的核心假設"

# 產出 Anki 卡片（Phase 2）
python3 skills/academic-edu-assistant/scripts/run_all.py \
    --query "認知心理學中的注意力資源理論" \
    --anki
```

---

## 📊 常用工作流組合

### 工作流一：完整的「新課堂」流程（最常用）

```bash
# Step 1：建立科目資料夾，丟入錄音和投影片
mkdir -p data/raw/社會心理學
cp ~/Downloads/lecture_03.m4a data/raw/社會心理學/
cp ~/Downloads/lecture_03_slides.pdf data/raw/社會心理學/
# （inbox_daemon 會自動路由 — m4a 去語音工廠，_slides.pdf 去語音參考）

# Step 2：確認 inbox_daemon 有偵測到（查看日誌）
tail -20 data/audio-transcriber/logs/inbox_daemon.log

# Step 3：或者手動觸發處理
cd ~/Desktop/local-workspace/open-claw-sandbox
python3 skills/audio-transcriber/scripts/run_all.py --subject 社會心理學

# Step 4：完成後，在 Obsidian 打開 data/wiki/社會心理學/ 查看筆記
```

### 工作流二：處理論文/教科書（PDF 全量解析）

```bash
# Step 1：把教科書 PDF 放入 inbox（注意後綴）
cp ~/Downloads/social_psych_textbook.pdf data/raw/社會心理學/social_psych_textbook.pdf
# 沒有特殊後綴 → 預設走 doc_parser 模式

# Step 2：手動觸發 doc-parser
python3 skills/doc-parser/scripts/run_all.py --subject 社會心理學

# Step 3：完成後編譯到 wiki
python3 skills/knowledge-compiler/scripts/run_all.py --subject 社會心理學
```

### 工作流三：重新強化已有筆記（二次加工）

```bash
# 對現有筆記重新做重點標注
python3 skills/smart_highlighter/scripts/highlight.py \
    --subject 社會心理學 \
    --input-file data/wiki/社會心理學/lecture_03.md \
    --output-file data/wiki/社會心理學/lecture_03.md

# 對現有筆記重新生成結構化總結
python3 skills/note_generator/scripts/synthesize.py \
    --subject 社會心理學 \
    --label "lecture_03" \
    --input-file data/wiki/社會心理學/lecture_03.md \
    --output-file data/wiki/社會心理學/lecture_03_summary.md
```

### 工作流四：新增自定義 PDF 後綴規則

```bash
# 查看現有規則，確認沒有重複
python3 skills/inbox-manager/scripts/query.py list

# 新增你的自定義規則
python3 skills/inbox-manager/scripts/query.py add \
    --add _exam \
    --routing both \
    --description "考試用材料 — 同時解析 + 語音校對參考"

# 驗證新規則已加入
python3 skills/inbox-manager/scripts/query.py list | grep _exam
```

---

## 🔍 常用狀態查詢指令

```bash
# 查看 inbox_daemon 的最新日誌（確認是否有偵測到新檔案）
tail -f data/audio-transcriber/logs/inbox_daemon.log

# 查看特定科目的語音處理進度
cat data/audio-transcriber/state/認知心理學.json | python3 -m json.tool

# 查看 doc-parser 的 inbox 狀態
python3 skills/doc-parser/scripts/run_all.py --scan --subject 認知心理學

# 列出 wiki 中已完成的科目
ls data/wiki/

# 檢查 Ollama 是否正在運行
curl http://localhost:11434/api/tags 2>/dev/null | python3 -m json.tool | grep name
```

---

## ❓ 常見問題 (FAQ)

### Q1：我丟了檔案進 `data/raw/`，但管線沒有自動啟動？

`inbox_daemon` 需要 `start.sh` 先啟動才會在背景監控。確認服務已啟動：
```bash
./infra/scripts/start.sh
```
或手動觸發：
```bash
python3 skills/audio-transcriber/scripts/run_all.py --subject <科目名>
```

### Q2：處理到一半程式當掉，怎麼辦？

使用 `--resume` 旗標從 checkpoint 繼續：
```bash
python3 skills/audio-transcriber/scripts/run_all.py --subject 認知心理學 --resume
```

### Q3：我想完全重跑某個科目，忽略所有進度記錄？

使用 `--force` 旗標：
```bash
python3 skills/audio-transcriber/scripts/run_all.py --subject 認知心理學 --force
```

### Q4：如何知道目前哪些後綴會被路由到哪個模式？

```bash
python3 skills/inbox-manager/scripts/query.py list
```

### Q5：`note_generator` 和 `smart_highlighter` 跟管線是什麼關係？

它們已內建在 `audio-transcriber`（Phase 4/5）和 `doc-parser`（Phase 2/3）的最後步驟中，正常跑管線就會自動執行。上面的 CLI-4 和 CLI-5 教程是讓你對**任意獨立的 Markdown 文件**單獨使用它們。

### Q6：程式碼裡有些地方提到 "Notion Synthesis"，Notion 同步功能在哪裡？

早期架構確實嘗試過直接同步 Notion，但後來轉向**本地優先**架構。`05_notion_synthesis.py` 現在產出的是相容 Obsidian 的 Markdown 筆記，統一存放在 `data/wiki/`。如需 Notion，可直接將 `data/wiki/` 資料夾匯入。

### Q7：執行時出現 `Permission denied` 或腳本無法啟動怎麼辦？

系統內建了全域環境自癒腳本，若遇到 `Permission Error`（特別是 `.sh` 檔案沒有執行權限時），請執行以下指令：
```bash
chmod +x infra/scripts/fix_perms.sh
./infra/scripts/fix_perms.sh
```
這會掃描專案內所有的 Shell 腳本並自動賦予執行權限。

### Q8：什麼是 macOS 原生通知？我要怎麼開啟？

本系統（包含所有 8 個子技能）已全域內建 `osascript` 通知支援。當你啟動任何較為耗時的管線（如語音轉錄、知識編譯），或者按下 `Ctrl+C` 中斷時，系統會自動透過 macOS 通知中心推播進度（例如「🏁 Pipeline 執行完畢」）。此功能為原生支援，**無需額外設定或安裝任何軟體**。
