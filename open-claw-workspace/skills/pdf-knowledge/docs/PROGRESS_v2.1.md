# PROGRESS.md — Project Milestones (V2.1)

---

## [2026-04-15] — V2.2: Dual-Skill Alignment & Core Expansion
- **Milestone**: Aligned project-level OOP guidelines with `voice-memo`. Absorbed `core/text_utils.py` chunking utility logic and mapped out MacOS deployment specifications (`bootstrap.sh`, `requirements.txt`).
- **Status**: ✅ Phase 1 Core Alignment Completed

## [2026-04-13] — V2.1: Domain Logic + Claude Skill Integration

- **Milestone**: 整合 Gemini 8 項建議（全部確認採納）+ Claude pdf-reading Skill 的三大技術升級。架構完全鎖定，準備進入 Stage 0.1 實作。
- **Status**: 🏗️ Architecture Fully Locked — Ready for Implementation

**新增的設計決策（D017-D024）**:
- D017：poppler-utils 前置診斷（Claude pdf-reading Skill）
- D018：向量圖表 pdftoppm 補充（Claude pdf-reading Skill，解決 matplotlib/R 圖遺漏問題）
- D019：OCR per-word 信心分數（Claude pdf-reading Skill + pytesseract 200 DPI）
- D020：術語雙層保護（priority_terms.json + Prompt 注入）
- D021：跨批次 global_session_memory.json
- D022：green_care_potential = null → Gemini 判斷 → 手動覆寫（使用者方案 B）
- D023：懸浮預覽 Flask API + URL fallback（使用者方案 B）
- D024：Marp Slide 2 = Agent Loop 後 Gemini 提取（使用者方案 B）

**已解決的問題總計**: 20 個潛在問題全部有對應方案，Gemini 建議的 8 項全部採納。

---

## 版本歷史

| 版本 | 里程碑 | 狀態 |
| :---: | :--- | :---: |
| V1.0 | 初始架構 | ✅ |
| V1.1 | 多欄 + 分批 + Voyager 時序 | ✅ |
| V2.0 | 安全 + 斷點續傳 + Core 整合 | ✅ |
| V2.1 | 領域邏輯 + Claude Skill + Gemini 建議 | ✅ |
| V2.2 | Stage 0: Security + Engine | ⏳ |
| V2.3 | Phase 0+1: Queue + Extraction | ⏳ |
| V2.4 | Phase 2+3: Triage + Agent Loop | ⏳ |
| V2.5 | Phase 4+5: Fact-Check + Interface | ⏳ |
| V3.0 | 養雞學 + 知識圖譜 + 多 Gem 並發 | ⬛ |
