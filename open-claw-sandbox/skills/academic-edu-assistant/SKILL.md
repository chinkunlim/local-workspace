---
name: academic-edu-assistant
description: "Academic & Education Assistant. RAG-based cross-comparison engine and Anki flashcard generator."
metadata:
  {
    "openclaw":
      {
        "emoji": "🎓"
      }
  }
---

# Academic & Education Assistant (學術與教學專武)

**Open Claw Skill**

## 角色與定位
專為深度學習、研究與備考設計的進階工具。它能處理多篇文獻的交叉比對，並自動從筆記中產出 Anki 記憶卡片。

## 管線階段 (Phases)
1. **Phase 1: 交叉比對 (`p01_compare.py`)**：讀取 `input/<subject>/` 下的多篇文章，進行對比並輸出綜合比較報告到 `01_comparison`。
2. **Phase 2: Anki 記憶卡 (`p02_anki.py`)**：讀取先前的報告或原始筆記，提煉為可以直接匯入 Anki 的 CSV 格式。

## 使用方式
請將要比對的 Markdown 檔案放入 `data/academic-edu-assistant/input/你的自訂主題名稱/` 中。
然後執行：
```bash
python scripts/run_all.py
```

## 全域標準化 (Omega Integration)

- **統一 CLI 介面**: 所有啟動腳本皆具備三大標準機制：
  1. **啟動前置檢查 (Preflight Check)**：驗證依賴與配置無誤。
  2. **狀態與 DAG 追蹤面板 (Dashboard)**：即時視覺化顯示管線進度。
  3. **互動選取與重跑機制 (Interactive Menu)**：可動態選擇 PENDING 或 COMPLETED 任務。
- 支援 macOS 原生系統通知 (osascript)，並具備 `KeyboardInterrupt` 優雅中斷與斷點保存功能。
