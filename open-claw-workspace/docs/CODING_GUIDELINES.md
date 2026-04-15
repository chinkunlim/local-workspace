# Open Claw Project - Master Coding Guidelines
> [!IMPORTANT]
> **全局核心指導原則**：這是一份專為邊緣設備（16GB macOS）打造的全本機系統。所有新擴充的 Skills、系統維護、或 AI 自動編程，**必須嚴格遵循**本指南中的資源驗證與架構哲學。

---

## 🏗️ 第一維度：系統架構與設計哲學 (Architecture & Philosophy)

1. **極致本地原生 (Local-First & No Docker)**
   - **禁止容器化包袱**：為確保深度調用 Apple Silicon (Metal Performance Shaders, MPS) 與 CPU 極致效能，絕不強加 Docker。
2. **強物件導向繼承制 (OOP Base Architecture)**
   - **強制繼承基底**：所有業務腳本 (Script) 與工具類，**絕對不得**寫成 Procedural Script。必須全面繼承工作區根目錄的 `core.pipeline_base.PipelineBase` 類別。
   - **解耦核心與技能**：路徑管理、`State Manager` (狀態庫)、`Resume Manager` (斷點續傳)、硬體監控 (`check_system_health`) 必須收斂在 `core/` 下。個別 Skill 只實作 `run(self)` 以及私有邏輯。
3. **目錄結構與配置層分離 (Separation of Concerns)**
   - **執行庫分離**：所有的狀態記錄、中間產物與除錯日誌，必須放進 `data/[skill_name]/` 下。
   - **配置與邏輯分離**：所有的 `config.yaml` 或提示詞檔案 (Prompt) 必須統一收納於 `skills/[skill_name]/config/` 之中。

---

## 💾 第二維度：資源防禦與記憶體管理 (Resource Defense)

1. **記憶體生命週期與優雅卸載 (Graceful Unload)**
   - 模型、重型資源分配策略必須是互斥的。例如當 Playwright 或 Docling (耗能 ~2.5GB) 執行時，LLM 必須主動卸載。
   - 階段完成或中斷時，強制呼叫 `unload_model()` 或 `gc.collect()` 將 VRAM 與 RAM 交還。
2. **智能切割與上下文守衛 (Context Window Guard)**
   - 14B 級別以上的模型，`num_ctx` **嚴禁突破 16384** (避免高壓 Swap 摧毀系統流暢度)。遇到超大文本需採用 `smart_split` 進行 Map-Reduce。
3. **輕量診斷與前置快速退出 (Fail-Fast Policy)**
   - 在執行高記憶體耗用任務前（如 PDF 解析），必須先執行毫秒級別的輕量腳本掃描。若判定無法處理（如加密失敗），立即終止並隔離，保護記憶體不被無端浪費。

---

## ⚙️ 第三維度：可維護性與動態配置 (Config & Scalability)

1. **打火機哲學（零硬編碼 No Hardcoding）**
   - 模型選擇、選項閥值、路徑、甚至是 CSS Selector，絕對不允許寫在 `.py` 的變數裡，需全數由 `config.yaml` 讀取。
2. **型別標註與因果註解 (Type Hints & Contextual Docstrings)**
   - 所有函數標註明確的型別（如 `-> List[Dict]`）。
   - **只寫「為什麼 (Why)」，不寫「是什麼 (What)」**：防禦性與商業邏輯需寫明初衷，例如為什麼要採用雙層驗證機制。
3. **保護術語與冪等自癒 (Idempotency & Resilience)**
   - 所有修改操作必須對應 Hash 狀態的驗證（`State Manager`）。程式中斷後，重新執行需能從最後一個完整的 Checkpoint 給予接續處理的選項。
   - LLM 輸出錯亂時，程式不應中斷，應進入 `Agentic Retry Loop` 嘗試自我修復指令。

---

## 👁️ 第四維度：使用者體驗與介面活性 (Runtime UX & Non-blocking)

1. **活著的終端機 (Alive Console)**
   - **嚴禁介面假死 (Freeze)**。舉凡網路請求、大型模型推論、檔案解析，皆必須掛載 Background Ticker Thread（如 Spinner / tqdm）來呈現動畫。
2. **專案級標準日誌格式 (Unified Emoji Logger)**
   - UI 訊息或 Log 必須掛載明確視覺化 Emojis：如 `🔍 偵測`, `🧠 運作中`, `✅ 完成`, `⚠️ 警告`, `❌ 錯誤`。
3. **產出純淨度保護 (Output Purity)**
   - 使用者體驗絕對乾淨。所有的 Console Meta、錯誤回溯、修改日誌，不可散落在產出文件的「文章主體」內，必須被完全隔離。

---

## 🤝 第五維度：頂尖 AI 協作與狀態同步 (Top-Tier AI Sync)

1. **極限高標準的角色代入 (Strict Expert Persona)**
   - 助手需預設自己是「頂級 Senior Backend/System Architect」。代碼需直接達到 Production-ready 級別。**沒有 MVP。**
2. **核心 Meta 文件自動更新機制**：
   每當大型變更完成，需主動去維護專案的工作簿狀態，不遺失上下文：
   - `handoff.md` / `task.md` / `walkthrough.md` 等進度與里程碑。
3. **自動 Git 版控同步 (Auto Local Commits)**：
   每一次測試確定通過，AI 助手必須執行 Local Git `add` / `commit` 來儲存還原點 (Rollback points)，編撰清晰的版本歷史脈絡。
