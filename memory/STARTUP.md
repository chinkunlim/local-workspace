# AI Startup Protocol & Session Initialization

> **Target Audience:** Development AIs (Google Antigravity, Claude Code, GitHub Copilot)
> **Purpose:** Defines the canonical startup prompt and full execution process for every new conversation.
> **Last Updated:** 2026-05-05

---

## Standard Startup Prompt (每次新對話複製貼上)

> Copy and paste the following block at the beginning of every new conversation.

```
請先讀取 identity/AI_PROFILE.md，完成以下完整 Startup Sequence：

【Phase 1 — 記憶載入】
1. 讀取 identity/AI_PROFILE.md（角色定義、操作原則、禁止行為）
2. 讀取 memory/PROJECT_RULES.md（行為合約、硬體限制、完工流程、Code Review Checklist）
3. 讀取 memory/HANDOFF.md（上次對話在哪裡停止）
4. 讀取 memory/TASKS.md（目前待辦事項）
5. 讀取 docs/STRUCTURE.md（完整專案目錄地圖）
6. 讀取 memory/HISTORY.md（Session 索引，確認哪些已封存）
7. 讀取 memory/DECISIONS.md（架構決策紀錄，避免推翻已有決定）
8. 讀取 docs/CODING_GUIDELINES.md §15（AI-Native 文件系統規範）

【Phase 2 — 靜態分析（自動執行）】
cd open-claw-sandbox && ./ops/check.sh
（涵蓋 Ruff lint + Ruff format + Mypy，覆蓋 core/ + skills/ 共 133 個檔案）

【Phase 3 — 人工審查（逐項執行 PROJECT_RULES.md §6 Checklist）】
1. 無裸露 print()
2. 無硬編碼路徑
3. 所有 LLM 呼叫後有 unload_model()
4. 所有寫入使用 AtomicWriter
5. 所有設定讀取走 config_manager
6. DRY 合規
7. STRUCTURE.md 與實際目錄一致
8. HANDOFF.md 時間戳是最新的
9. 無無引用的 # TODO
10. 所有原則已被「✅ 原則已記錄」確認

【Phase 4 — 文件同步核對】
- git -C open-claw-sandbox status
- git -C open-claw-sandbox log --oneline -5
- 確認所有 .md 檔案（ARCHITECTURE.md / CHANGELOG.md / STRUCTURE.md）已反映最新狀態

【Phase 5 — Continuous Principle Sync】
- 掃描上次對話的 memory/sessions/ 最新 session 檔案
- 提取任何尚未寫入 md 的原則，補齊並以「✅ 原則已記錄」格式確認

完成後，給我一份「專案狀態報告」，格式如下：

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 專案狀態報告 [YYYY-MM-DD HH:MM]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
① 程式碼品質
   Ruff:  ✅ / ❌ (N errors)
   Mypy:  ✅ / ❌ (N errors in N files)

② Git 狀態
   Branch: main
   Pending changes: 無 / 有 (列出檔案)
   Last commit: <hash> <message>

③ 文件同步
   需要更新: 無 / 有 (列出 md 檔案名稱與原因)

④ 待辦事項 (from TASKS.md)
   - <item 1>
   - <item 2>

⑤ 上次封存的 Session
   <session filename> — [Archived] ✅ / 尚未封存 ⚠️
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

報告完畢後，等待我下達新任務。
```

---

## 完整處理過程說明

### Phase 1 — 記憶載入 (Context Bootstrap)

| 步驟 | 讀取檔案 | 目的 |
|:---:|:---|:---|
| 1 | `identity/AI_PROFILE.md` | 確認角色、操作原則、啟動指令、禁止行為 |
| 2 | `memory/PROJECT_RULES.md` | 載入行為合約、硬體限制、完工流程、Code Review Checklist |
| 3 | `memory/HANDOFF.md` | 了解上次在哪裡停止、有無未完成項目 |
| 4 | `memory/TASKS.md` | 目前待辦事項的完整清單 |
| 5 | `docs/STRUCTURE.md` | 建立完整的專案目錄地圖 |
| 6 | `memory/HISTORY.md` | 確認哪些 Session 已封存（有 `[Archived]` 標籤） |
| 7 | `memory/DECISIONS.md` | 避免推翻已有的架構決策 |
| 8 | `docs/CODING_GUIDELINES.md §15` | AI-Native 文件系統規範 |

> [!IMPORTANT]
> 不能跳過任何步驟，也不能猜測專案狀態。必須讀完才能開始任何程式碼操作。

---

### Phase 2 — 靜態分析 (Automated Quality Gate)

執行 `cd open-claw-sandbox && ./ops/check.sh`，涵蓋：

| 工具 | 檢查範圍 | 標準 |
|:---|:---|:---|
| Ruff lint | 全部 .py 檔案 | 0 errors（可 auto-fix 者先修） |
| Ruff format | 全部 .py 檔案 | 0 formatting issues |
| Mypy | `core/` + `skills/`（133 個檔案） | 0 type errors |

---

### Phase 3 — 人工審查 (Manual Pattern Review)

依照 `PROJECT_RULES.md §6 Code Review Checklist` 逐項執行：

```bash
# 1. 無裸露 print()
grep -rn "^print(" core/ skills/

# 2. 無硬編碼路徑
grep -rn '/data/raw\|/tmp/openclaw' core/ skills/

# 3. 所有 LLM 呼叫後有 unload_model()
grep -rn "llm.generate\|llm.async_generate" core/ skills/ --include="*.py"

# 4. 所有寫入使用 AtomicWriter
grep -rn "open(.*[\"']w[\"']" core/ skills/

# 5. 所有設定讀取走 config_manager
grep -rn "yaml.load\|open.*config.yaml" core/ skills/

# 9. 無無引用的 # TODO
grep -rn "# TODO" core/ skills/
```

其餘項目（6 DRY、7 目錄一致、8 時間戳、10 原則確認）為語意審查，不依賴 grep。

---

### Phase 4 — 文件同步核對 (SSoT Verification)

```bash
git -C open-claw-sandbox status
git -C open-claw-sandbox log --oneline -5
```

逐一核對：
- `docs/STRUCTURE.md` 是否反映實際目錄結構
- `CHANGELOG.md` 是否記錄最近的變更
- `skills/<skill>/SKILL.md` 是否已過時
- `memory/HANDOFF.md` 的 `Last Updated` 是否為今日

---

### Phase 5 — Continuous Principle Sync

- 掃描 `memory/sessions/` 中最新的 Session 檔案
- 提取任何在對話中出現但尚未寫入 md 的原則
- 路由到正確的 md 檔案（依照 `AI_PROFILE.md` 的路由表）
- 每條原則必須以以下格式確認：
  > `✅ 原則已記錄 → [target_file.md]：<rule content>`

---

### End-of-Session 完工流程

```
1. check.sh    → 確保 ✅ All checks passed
2. 更新所有相關 md 檔案
3. git add -A && git commit -m "..." && git push   ← 先推
4. python3 ops/archive_session.py                   ← 推完再封存
5. 更新 memory/HANDOFF.md & memory/TASKS.md
```

> [!IMPORTANT]
> `archive_session.py` 必須在 `git push` **之後**執行，否則對話尾端可能被截斷，無法完整封存。

---

## 原則路由表（快速參考）

| 觸發情境 | 路由目標 |
|:---|:---|
| 操作習慣、Prompt Macro、溝通風格 | `identity/AI_PROFILE.md` |
| 程式語法規範、命名規則、格式標準 | `docs/CODING_GUIDELINES.md` |
| IDE 限制、執行協議、完工流程 | `memory/PROJECT_RULES.md` |
| Sandbox Agent 倫理、邊界定義 | `open-claw-sandbox/SOUL.md` |
| 為什麼選 X 不選 Y（架構決策） | `memory/DECISIONS.md` |
| 目錄結構、資料路徑、核心模組變更 | `docs/STRUCTURE.md` |
| CLI 介面、使用者操作說明 | `skills/<skill>/SKILL.md` |
