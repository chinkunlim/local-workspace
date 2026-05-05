# [Archived] 完美主義者級別程式架構對齊 (Enterprise-Grade Strict Alignment)

> **Date:** Unknown
> **Session ID:** `d133d678`

---

## 1. Implementation Plan

# 完美主義者級別程式架構對齊 (Enterprise-Grade Strict Alignment)

身為一個有嚴重程式碼潔癖與強迫症的架構師，我用最嚴格的標準重新檢視了整個 Open Claw 專案，發現目前的系統雖然在「巨觀架構」上已分離，但在「微觀程式碼素質」與「底層機制共用」上仍有妥協的痕跡！這些容忍與技術債是我們絕對不能接受的。

## 🎯 診斷出之不一致與妥協點 (Gap Analysis)

1. **核心類別參數的「向下相容妥協」 (The Compatibility Hack)**：
   在 `core/pipeline_base.py` 第 35 行中，您給 `skill_name` 預設了 `"voice-memo"` 的值！這在物件導向設計中是極度醜陋的 hack。一個抽象的底層工具不應該知道某個實作套件的名稱。
2. **型別與資料結構斷層 (Typing and Structure Gap)**：
   `pdf-knowledge` 採取了嚴謹的 `dataclass` 與 `typing` 函式庫，而 `voice-memo` 部分老舊代碼仍仰賴沒有結構定義的 `dict`。
3. **安全機制的偏科 (Security Isolation)**：
   `pdf-knowledge` 規劃了嚴厲的 Web 安全審計與沙盒，但這些全域的安全機制尚未被提煉到 `core/` 下面供所有套件共用！

---

## 🛠 Proposed Changes (整改方案)

### 1. 撲殺預設值並強制參數聲明
#### [MODIFY] [pipeline_base.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/core/pipeline_base.py)
- **刪除預設值**：將 `def __init__(..., skill_name: str = "voice-memo")` 修改為 `def __init__(..., skill_name: str)`。強制所有套件報上自己的大名。

#### [MODIFY] [voice-memo/scripts/phases/*.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/phases/)
- 改寫這六支檔案 (`phase0`~`phase5`) 裡的 `super().__init__()`，強制宣告 `skill_name="voice-memo"`，補足物件導向的嚴謹度。

### 2. 極端嚴格的代碼風格法典
#### [MODIFY] [CODING_GUIDELINES.md](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/docs/CODING_GUIDELINES.md)
- 新增「**第六維度：強迫症級別程式碼規範 (Draconian Code Styles)**」。
- 明文規定：強制使用 `typing` (Dict, List, Optional)、Google Style Docstrings (包含 Args, Returns, Raises 段落)、並全面用 `dataclass` 取代鬆散的 dictionary 操作。禁止任何 `Exception: pass` 吞噬錯誤的無聲失敗。

### 3. 未來共用安全核心的預留
- （非本次修改內容，但列入架構藍圖）將 `pdf-knowledge` 的 Security Manager 機制拉升到 `open-claw-workspace/core/security.py`，未來只要有 URL 操作，即便是 `voice-memo` 也必須受限於該元件管控。

---

## 🛑 Open Questions (需您定奪)

1. **命名風格（Naming Convention）**：`voice-memo` 大量使用 `phase1_XXX.py` 來呈現線性關係，而 `pdf-knowledge` 則使用功能描述（如 `queue_manager.py`、`pdf_diagnostic.py`）。身為完美主義者，您是否要求我將 `pdf-knowledge` 也加上如 `p0_queue_manager.py`, `p1_diagnostic.py` 來達成宇宙級距的一致性？還是您承認兩者的非同步與線性架構本質不同，允許這層差異？
2. **是否執行 PipelineBase 參數重構**？只要您一聲令下，我立刻把 `pipeline_base.py` 的妥協參數拔掉，並自動更新所有 Voice Memo 的依賴。


---

## 2. Walkthrough / Summary

# 全局化開發指標系統建立完成！

為呼應 Open Claw 體系越來越大的程式庫，所有「撰寫與開發程式的信仰」都已被抽離，成為全專案最上層的最高指導原則！

## 📚 1. 最高指導原則 (CODING_GUIDELINES.md)
路徑：`open-claw-workspace/docs/CODING_GUIDELINES.md`  

✅ 已揉合兩個 Skill 裡的精華概念：
- 第一維度：系統架構與分離式配置理念 (Local-First 面向)
- 第二維度：資源防禦策略 (記憶體榨取保護、Fail-Fast 診斷退出)
- 第三維度：零硬編碼設定 (YAML 組態層)
- 第四維度：使用者體驗 UX與介面活性 (Spinners / Emojis / 日誌規格)
- 第五維度：頂尖 AI 協作原則 (6大Meta文件同步要求)

## 🗃️ 2. 套件邏輯歸檔 (ARCHITECTURE.md)
原本寫有各 Skills 特性與流程邏輯的段落，經過刪減掉上述的通用規矩後，已經被優雅地更名為**業務架構白皮書**：
- `voice-memo/docs/ARCHITECTURE.md`
- `pdf-knowledge/docs/ARCHITECTURE.md`

這個更名使「專案信仰」與「特定功能」完全解耦，這正是軟體架構中最健康的狀態！

## 💣 3. 掃雷行動 - 清除 Core 幽靈殘留物！
這個連鎖反應修正了一項超級大的架構問題：
✅ 刪除了殘留在 `skills/voice-memo/scripts/core` 中的舊模組。  
✅ 改寫了高達 10 份 Python (`*.py`) 裡的 `sys.path.append` 架構層級。  
✅ 現在不管任何 `.py` 執行檔，都會**乖乖穿透 3 層資料夾 (`../../../`)** 回到真正的 `open-claw-workspace/core/` 呼叫最新的 `pipeline_base.py`！


---

## 3. Tasks Executed

# 全局指南重構清單

## 1. 創立全局標準 (Global Standards)
- [x] 撰寫工作區層級的 `docs/CODING_GUIDELINES.md`

## 2. 移除幽靈模組與修正引用 (Ghost Module Fixing)
- [x] 修正 `skills/voice-memo/scripts/run_all.py` 的 `sys.path.append`
- [x] 修正 `skills/voice-memo/scripts/phases/` 內所有檔案的 `sys.path.append`
- [x] 徹底刪除殘留的 `skills/voice-memo/scripts/core/` 

## 3. 領域邏輯歸檔 (Logic Architecture Specs)
- [x] 刪修 `skills/voice-memo/docs/CODING_GUIDELINES.md` 變更為 `ARCHITECTURE.md`
- [x] 刪修 `skills/pdf-knowledge/docs/CODING_GUIDELINES_v2.1.md` 變更為 `ARCHITECTURE.md`
- [x] 移除舊有同名 `.md` 檔案

