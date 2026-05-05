# [Archived] PDF Knowledge Skill — Implementation Plan

> **Date:** Unknown
> **Session ID:** `871e6d22`

---

## 1. Implementation Plan

# PDF Knowledge Skill — Implementation Plan

根據 `skills/pdf-knowledge/docs/` 內的架構文件（V2.1），為 open-claw-workspace 建立完整的 pdf-knowledge skill，同時重構 voice-memo 以使用共用的 `core/` 框架。

---

## 核心設計決策

> [!IMPORTANT]
> **共用框架位置變更**：根據 CLAUDE_v2.1.md，`core/` 應置於 workspace root（`open-claw-workspace/core/`），供兩個 skill 共用。目前的 `voice-memo/scripts/core/` 將被替換為指向 shared core 的引用。

> [!IMPORTANT]
> **Stage 0.1 優先**：HANDOFF_v2.1.md 明確標記當前狀態為「Architecture Fully Locked. Ready for Stage 0.1 Implementation」。我們將實作 Stage 0.1（Security Foundation）和 Stage 0.2（PDF Engine），這是 PDF 管道運行的最小可行前提。

---

## 架構圖

```
open-claw-workspace/
├── core/                          ← [NEW] 兩個 Skill 共用框架
│   ├── __init__.py
│   ├── pipeline_base.py           ← 從 voice-memo/scripts/core/ 移入
│   ├── state_manager.py           ← 從 voice-memo/scripts/core/ 移入
│   ├── llm_client.py              ← 從 voice-memo/scripts/core/ 移入
│   ├── security_manager.py        ← [NEW] PDF Skill 貢獻
│   └── resume_manager.py          ← [NEW] PDF Skill 貢獻
│
├── skills/
│   ├── SKILL.md                   ← [MODIFY] 加入 pdf-knowledge
│   │
│   ├── voice-memo/
│   │   ├── SKILL.md               ← [MODIFY] 更新 core/ 路徑說明
│   │   ├── docs/                  ← 不動
│   │   └── scripts/
│   │       ├── core/              ← [MODIFY] 改為引用 workspace root core/
│   │       │   └── __init__.py    ← 改成 re-export shim
│   │       ├── phases/
│   │       ├── utils/
│   │       ├── run_all.py
│   │       └── prompt.md
│   │
│   └── pdf-knowledge/
│       ├── SKILL.md               ← [NEW]
│       ├── docs/                  ← 現有文件（不動）
│       ├── config/                ← [NEW]
│       │   ├── config.yaml
│       │   ├── security_policy.yaml
│       │   ├── selectors.yaml
│       │   └── priority_terms.json
│       └── scripts/               ← [NEW]
│           ├── main_app.py
│           ├── inbox_watcher.py
│           ├── queue_manager.py
│           ├── pdf_diagnostic.py   ← Stage 0.2
│           ├── pdf_engine.py       ← Stage 0.2
│           ├── vector_chart_extractor.py ← Stage 0.2
│           └── ocr_quality_gate.py ← Stage 0.2
│
└── data/
    └── pdf-knowledge/             ← [NEW] Pipeline runtime data
        ├── 01_Inbox/
        ├── 02_Processed/
        ├── 03_Agent_Core/
        ├── 05_Final_Knowledge/
        ├── Error/
        ├── library/
        └── vector_db/
```

---

## Proposed Changes

### 1. Shared Core Framework

#### [NEW] `core/__init__.py`
Re-export all shared classes for clean imports.

#### [MODIFY] `voice-memo/scripts/core/__init__.py`
改為 shim，從 workspace root `core/` re-export，保持 voice-memo 現有的 `from .core.pipeline_base import PipelineBase` 語法相容。

#### [NEW] `core/security_manager.py`
Playwright 操作授權邊界管理器。實作：
- `validate_navigation(url)` — 根據 `security_policy.yaml` 白名單檢查
- `validate_action(action_type, target)` — 動作授權
- `SecurityViolationError` exception
- `security_audit.log` 寫入

#### [NEW] `core/resume_manager.py`
跨 Session 斷點續傳。實作：
- `save_checkpoint(pdf_id, phase, chunk_index)`
- `check_resumable(pdf_id)` → `resume_state.json`
- `resume_from(pdf_id)` → 返回恢復點

---

### 2. PDF Knowledge Scripts (Stage 0.2)

#### [NEW] `skills/pdf-knowledge/scripts/pdf_diagnostic.py`
Phase 1a 輕量診斷（< 50MB RAM，< 5秒）：
- `run_pdfinfo()` — 頁數、版本、加密
- `run_pdftotext_sample()` — 掃描偵測（首頁 < 50字）
- `run_pdffonts()` — 字型健康診斷
- `run_pdfimages_list()` — raster 圖片統計
- `detect_vector_chart_pages()` — 向量圖表頁碼
- `detect_multi_column()` — 多欄偵測
- 輸出 `scan_report.json`

#### [NEW] `skills/pdf-knowledge/scripts/pdf_engine.py`
Phase 1b Docling 深度提取：
- Docling 呼叫 + `gc.collect()` 記憶體釋放
- 字型損壞 fallback（pdftoppm + OCR 交叉驗證）
- 輸出 `raw_extracted.md`（IMMUTABLE）

#### [NEW] `skills/pdf-knowledge/scripts/vector_chart_extractor.py`
Phase 1c 向量圖表補充：
- `pdftoppm -jpeg -r 150` 光柵化
- 存入 `assets/fig_p{n}_vector.jpg`
- 更新 `figure_list.md` 標記 `type="vector_rasterized"`

#### [NEW] `skills/pdf-knowledge/scripts/ocr_quality_gate.py`
Phase 1d OCR 品質評估：
- `pytesseract.image_to_data()` per-word 信心分數
- 200 DPI + `chi_tra+eng`
- 門檻 0.80，低於觸發警告
- 更新 `scan_report.json` 的 `low_confidence_pages`

#### [NEW] `skills/pdf-knowledge/scripts/queue_manager.py`
Phase 0 佇列管理（基本骨架）：
- 串行處理（ModelMutex）
- `check_system_health()` 前置
- 首次設定引導

#### [NEW] `skills/pdf-knowledge/scripts/inbox_watcher.py`
PDF 入匣監視器：
- Watchdog 目錄監控
- 三層去重（已處理/佇列中/MD5）
- 加密偵測

#### [NEW] `skills/pdf-knowledge/scripts/main_app.py`
Flask 主應用（最小可用版）：
- Dashboard 狀態顯示
- 手動觸發診斷/處理
- `resume_state` 掃描

---

### 3. Configuration Files

#### [NEW] `skills/pdf-knowledge/config/config.yaml`
所有路徑、模型名、閾值（零硬編碼）

#### [NEW] `skills/pdf-knowledge/config/security_policy.yaml`
Playwright 授權邊界（只有使用者可修改）

#### [NEW] `skills/pdf-knowledge/config/selectors.yaml`
所有 Playwright DOM selectors 集中管理

#### [NEW] `skills/pdf-knowledge/config/priority_terms.json`
關鍵術語強制保護清單

---

### 4. SKILL.md Updates

#### [MODIFY] `skills/SKILL.md`
加入 pdf-knowledge skill 條目，讓 Open Claw 能調度此 skill。

#### [NEW] `skills/pdf-knowledge/SKILL.md`
pdf-knowledge skill 的完整操作指南，參考 voice-memo/SKILL.md 格式。

---

### 5. Data Directories

#### [NEW] `data/pdf-knowledge/`
建立所有 pipeline runtime 資料夾結構。

---

## Voice-Memo 調整說明

> [!NOTE]
> voice-memo 現有的 `scripts/core/` 將改為 **shim module**，re-export 來自 workspace root `core/` 的類別。這樣：
> 1. 現有的所有 `phase*.py` 的 import 語法**不需要修改**
> 2. 實際共用邏輯在 `core/` 統一維護
> 3. 未來 pdf-knowledge 的 phases 也可用同樣的 import pattern

Voice-memo 的 `pipeline_base.py` 中有一個 voice-memo 特有的路徑：
```python
self.base_dir = os.path.join(self.workspace_root, "data", "voice-memo")
```
這需要在 `PipelineBase.__init__` 加入 `skill_name` 參數，使其通用化：
```python
self.base_dir = os.path.join(self.workspace_root, "data", skill_name)
```

---

## Verification Plan

### Automated Tests
```bash
# 1. 驗證 core/ import 正確
python3 -c "from core.pipeline_base import PipelineBase; print('✅ core import OK')"

# 2. 驗證 voice-memo shim 相容
cd open-claw-workspace && python3 -c "from skills.voice_memo.scripts.core.pipeline_base import PipelineBase; print('✅ shim OK')"

# 3. 驗證 pdf_diagnostic 基本執行（乾跑，不需要真實 PDF）
python3 skills/pdf-knowledge/scripts/pdf_diagnostic.py --help

# 4. 驗證 security_manager
python3 -c "from core.security_manager import SecurityManager; print('✅ security_manager OK')"
```

### Manual Verification
- 確認 `voice-memo` Pipeline 原有的 `run_all.py` 仍可正常執行
- 確認 `SKILL.md` 的新增 pdf-knowledge 條目格式正確

---

## Open Questions

> [!IMPORTANT]
> 以下問題在 TASKS_v2.1.md 中標記為 Pending（Q003-Q007），不影響 Stage 0 實作，但建議在後續實作前確認：
> - **[Q003]** Chrome Profile 路徑（Playwright 需要）
> - **[Q007]** `priority_terms.json` 是否有其他高風險術語需要加入？


---

## 2. Walkthrough / Summary

*(No Walkthrough)*

---

## 3. Tasks Executed

# PDF Knowledge Skill — Task Tracker

## Phase 1: Shared core/ Framework
- [x] `core/__init__.py` — re-export shim
- [x] `core/pipeline_base.py` — add `skill_name` keyword param (backward compatible)
- [x] `core/state_manager.py` — copy from voice-memo core (generic)
- [x] `core/llm_client.py` — copy from voice-memo core (generic)
- [x] `core/security_manager.py` — NEW: Playwright auth boundary
- [x] `core/resume_manager.py` — NEW: cross-session resume

## Phase 2: voice-memo Shim Update
- [x] `voice-memo/scripts/core/__init__.py` — shim → re-export from workspace core/

## Phase 3: pdf-knowledge Config
- [x] `skills/pdf-knowledge/config/config.yaml`
- [x] `skills/pdf-knowledge/config/security_policy.yaml`
- [x] `skills/pdf-knowledge/config/selectors.yaml`
- [x] `skills/pdf-knowledge/config/priority_terms.json`

## Phase 4: pdf-knowledge Scripts (Stage 0.2)
- [x] `skills/pdf-knowledge/scripts/pdf_diagnostic.py`
- [x] `skills/pdf-knowledge/scripts/pdf_engine.py`
- [x] `skills/pdf-knowledge/scripts/vector_chart_extractor.py`
- [x] `skills/pdf-knowledge/scripts/ocr_quality_gate.py`
- [x] `skills/pdf-knowledge/scripts/queue_manager.py`
- [x] `skills/pdf-knowledge/scripts/inbox_watcher.py`
- [x] `skills/pdf-knowledge/scripts/main_app.py`

## Phase 5: SKILL.md Files
- [x] `skills/pdf-knowledge/SKILL.md`
- [x] `skills/SKILL.md` — add pdf-knowledge section

## Phase 6: Data Directory Structure
- [x] `data/pdf-knowledge/` subdirectory tree

