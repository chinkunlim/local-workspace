# OpenClaw 完整生態系架構與 15 大技能模組解析 (V3.0)

為了給您最透徹的全景觀，我們重新盤點了專案底下的 `skills` 目錄。OpenClaw 生態系目前總共搭載了 **15 個獨立的 Skill（技能模組）** 與 **3 個核心服務（Core Services）**。

這是一座具有高度擴充性的自動化知識工廠，所有的模組透過事件驅動 (Event-Bus) 與路由 (Router) 機制非同步交棒。以下是這座工廠的**六大樓層 (Layer)** 完整工作流程：

---

## 🏛️ 全景系統架構圖 (The 6 Layers)

```mermaid
graph TD
    %% --------------------------------
    %% 1. Ingestion & Management Layer
    %% --------------------------------
    subgraph 1. 資料收發與管理層
        A1[Telegram 機器人] -->|/idea 暫存排程| B(Inbox 收件匣)
        A2[手動丟入檔案] --> B
        B --> C[inbox_daemon 監聽]
        C -->|解析標籤/副檔名| D[router_agent 派發中樞]
        D <-->|動態讀取規則| E[inbox_manager 規則管理]
    end

    %% --------------------------------
    %% 2. Base Processing Layer
    %% --------------------------------
    subgraph 2. 基礎處理與萃取層
        D -->|影片 .mp4| F1[video_ingester]
        F1 -->|抽音軌| F2
        F1 -->|抽關鍵影格| F3(圖庫)

        D -->|語音 .mp3| F2[audio_transcriber]
        F2 -->|Whisper 逐字稿| F4[proofreader 人工校對]

        D -->|文件 .pdf| F5[doc_parser]
        F5 -->|OCR / VLM 視覺解析| F6(純文字)
    end

    %% --------------------------------
    %% 3. Interactive & Annotation Layer
    %% --------------------------------
    subgraph 3. 互動閱讀與智慧標註層
        F4 --> G1[smart_highlighter]
        F6 --> G1
        G1 -->|LLM 自動螢光筆與粗體標記| G2[interactive_reader]
        G2 -->|互動式標籤處理| G3(高易讀性文本)
    end

    %% --------------------------------
    %% 4. Knowledge Synthesis Layer
    %% --------------------------------
    subgraph 4. 知識提煉與總結層
        G3 --> H1[note_generator]
        
        D -->|對話紀錄/點子| H2[student_researcher]
        H2 -->|Phase 0: 語意路由| H3{ChromaDB 尋根或孵化 Incubator}
        H3 -->|基礎總結與嫁接| H4(初階綜合報告 _research.md)
        H3 -->|Phase 1: 論點萃取| H5(待查證 Claims)
    end

    %% --------------------------------
    %% 6. Compilation Layer (優先進入大腦)
    %% --------------------------------
    subgraph 6. 編譯與互動存取層
        H1 -->|常規總結| K1[knowledge_compiler]
        H4 -->|原味想法入庫| K1
        J3 -->|補充包入庫| K1
        
        K1 -->|圖譜抽取/排版| K2[(Obsidian Vault 雙向連結知識庫)]
        K1 -->|寫入向量庫| K3[(ChromaDB)]
        
        K3 <-->|RAG 檢索| L[telegram_kb_agent]
        L -->|回答問題| User(使用者)
    end

    %% --------------------------------
    %% 5. Deep Academic Layer (選擇性)
    %% --------------------------------
    subgraph 5. 學術輔助與深度學習層 (選擇性擴充分支)
        H5 -.->|發動查證| I1[academic_library_agent]
        I1 -->|Playwright 自動操作| I2(Elsevier 論文抓取)
        
        I2 -.->|發動辯證| I3[gemini_verifier_agent]
        I3 -->|Playwright 自動操作| I4(付費版 Gemini 邏輯辯證)
        
        H1 -.->|發動學習| J1[feynman_simulator]
        J1 -->|師生對答模擬| J2(深度理解問答錄)
        
        H1 -.->|發動複習| J4[academic_edu_assistant]
        J4 -->|產生記憶卡| J5(Anki 牌組與 RSS 追蹤)
        
        I4 -.->|產出| J3[延伸補充包 Extension]
        J2 -.->|產出| J3
    end
```

---

## 🔍 完整模組 (Skills) 詳細分析與工作流程

### 第 0 層：核心調度中樞 (Core Services)
這些是不屬於 `skills` 目錄，但維持整個專案心跳的底層服務：
1. **`inbox_daemon`**：24 小時監聽信箱，解析 `#tag` 以決定檔案的目標科目 (Subject)。
2. **`router_agent`**：大腦中樞。依據檔案特性與意圖（如 `.md:research`），規劃一條從頭到尾的技能接力路線 (Pipeline DAG)。
3. **`task_queue`**：單線程的背景任務佇列，確保高耗能的 AI 任務不會同時擠爆記憶體 (防 OOM 機制)。

### 第 1 層：資料收發與管理層 (Ingestion)
1. **`inbox_manager`**：管理員技能。這是一個 CLI 工具，當使用者透過指令想更改某類檔案（如 PDF）預設該走哪條路徑時，會呼叫此模組來修改底層的 `inbox_config.json` 規則表。
2. **`telegram_kb_agent` (前端入口)**：作為您的入口助理，您可以丟 `/idea` 給它，它會將靈感暫存並利用 APScheduler 在週末排程推播給您確認。

### 第 2 層：基礎處理與萃取層 (Base Extraction)
處理無結構多媒體的「苦力活」：
3. **`video_ingester`**：影片拆解。將 `.mp4` 分離出純音軌，並每隔幾秒擷取關鍵影格，留給視覺模型使用。
4. **`audio_transcriber`**：語音轉錄。呼叫 Whisper 模型，將音檔轉為高準確度的逐字稿（具備詞庫自動對齊功能）。
5. **`doc_parser`**：文件解析。包含 OCR 引擎與 VLM (Vision Language Model) 視覺模型，專門解析 PDF 上的複雜圖表與文字。
6. **`proofreader`**：人工校對 (HITL)。當語音轉譯出艱澀名詞時，系統在此暫停，開啟 UI 讓您一邊聽音檔一邊校正文本，保證基底資料正確。

### 第 3 層：互動閱讀與智慧標註層 (Interactive Annotation)
這是一層「加工作業」，讓長篇大論變得超級好讀：
7. **`smart_highlighter`**：**智慧螢光筆**。系統呼叫 LLM 閱讀過長文後，自動在原文上標記 `**粗體**` 與 `==螢光筆==`。此模組內建了「防篡改機制 (Anti-Tampering guard)」，保證 LLM 絕對不會誤刪您任何一句原文。
8. **`interactive_reader`**：**互動閱讀器**。針對解析後的文本進行互動式的標籤與章節重構，增加後續閱讀的易讀性。

### 第 4 層：知識提煉與總結層 (Knowledge Synthesis)
將好讀的草稿，正式濃縮為具有觀點的報告：
9. **`note_generator`**：常規筆記生成。將上述的資料總結為重點條列式 Markdown 筆記。
10. **`student_researcher`**：**靈感處理核心**（我們剛升級的模組）。
    - **Phase 0 (語意路由)**：利用 `ChromaDB` 比對向量找尋舊有關聯。無關聯則送入 `Incubator` 孵化器。
    - **快速總結**：生成帶有 `[[雙向連結]]` 的初階總結，**並立刻往下送往第 6 層入庫**，確保您原汁原味的點子立刻可以被瀏覽。
    - **Phase 1 (論點萃取)**：抓出值得深入研究的論點，留給第 5 層備用。

### 第 5 層：學術輔助與深度學習層 (Deep Academic - 選擇性擴充)
這是強大的**「視覺化自動網頁操作」**區塊。作為選擇性執行的分支，產出的結果會變成**「延伸補充包 (Extension)」**，保證不污染前一層的原味筆記。
11. **`academic_library_agent`**：操作 Playwright 瀏覽器，自動登入 Elsevier 等網站幫您找論文。
12. **`gemini_verifier_agent`**：操作 Playwright，將點子與論文丟入您付費版的 Gemini Web 介面，進行激烈的 AI 辯證。
13. **`feynman_simulator`**：化身為刁鑽的學生，對著您的筆記不斷追問，逼迫您把複雜概念解釋清楚。
14. **`academic_edu_assistant`**：學術教育助手。能攝取 RSS 追蹤最新領域文章，進行文獻對比，並**自動為您生成 Anki 記憶閃卡**。

### 第 6 層：編譯與互動存取層 (Compilation)
所有的產出最終收斂的地方（也就是您的大腦）：
15. **`knowledge_compiler`**：**知識編譯器**。
    - 處理 Obsidian 格式清洗。
    - `p02_extract_graph.py`：抽取您的筆記脈絡建立知識圖譜關聯。
    - 存入 `wiki/` 資料夾與更新 `INDEX.md`。
    - 將知識 Embedding 寫回 `ChromaDB` 向量資料庫。
- **`telegram_kb_agent` (後端互動)**：此時它扮演「隨身知識管家」。您可以透過 Telegram 發問，它會使用 RAG (Retrieval-Augmented Generation) 技術去 `ChromaDB` 撈取您專屬的筆記給出解答。

---

這樣一來，15 個 Skill 與核心服務各司其職，組成了這個會**自動消化資料、自動畫重點、自動查論文、甚至自動產出 Anki 記憶卡**的超級終身學習系統！
