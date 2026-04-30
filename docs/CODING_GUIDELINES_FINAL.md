# 專業程式開發完整準則手冊
> **版本：** v3.0.0
> **適用對象：** 所有開發者（Human & AI Agent）
> **適用工具：** VS Code / Cline、Claude Code、Google Antigravity、任何 IDE
> **適用規模：** 單人開發 → 小團隊 → 多人協作 → 開源
> **核心哲學：** 簡潔、健壯、可追溯、AI 友善

---

## 目錄

0. [手冊使用說明與 AI 協作協議](#0-手冊使用說明與-ai-協作協議)
1. [程式碼品質基礎原則](#1-程式碼品質基礎原則)
2. [SOLID 原則](#2-solid-原則)
3. [架構與設計原則](#3-架構與設計原則)
4. [錯誤處理與防禦性程式設計](#4-錯誤處理與防禦性程式設計)
5. [可維護性原則](#5-可維護性原則)
6. [測試原則](#6-測試原則)
7. [安全與效能原則](#7-安全與效能原則)
8. [程式碼風格與格式](#8-程式碼風格與格式)
9. [函數編寫完美主義細則](#9-函數編寫完美主義細則)
10. [命名規範](#10-命名規範)
11. [專案結構標準](#11-專案結構標準)
12. [手冊文件體系（Human + AI 雙軌）](#12-手冊文件體系human--ai-雙軌)
13. [Git 版本控制規範](#13-git-版本控制規範)
14. [環境變數與設定管理](#14-環境變數與設定管理)
15. [API 設計規範](#15-api-設計規範)
16. [自動化強制工具鏈](#16-自動化強制工具鏈)
17. [各階段啟用原則](#17-各階段啟用原則)
18. [禁止模式（Prohibited Patterns）](#18-禁止模式prohibited-patterns)
19. [快速參考總表](#19-快速參考總表)
20. [版本演進與背景記錄](#20-版本演進與背景記錄)

---

## 0. 手冊使用說明與 AI 協作協議

### 0.1 適用對象

本手冊是專案開發的「憲法」，強制適用於以下對象：

- **人類開發者**：作為 Code Review 與日常開發的最終準則
- **AI Agent**（Cline、Claude Code、Google Antigravity 等）：作為進入任何專案時的第一份讀物，必須加載為「核心上下文」

### 0.2 AI Agent 強制工作流程

> ⚠️ **所有 AI Agent 在執行任何任務前，必須依序完成以下步驟，嚴禁跳過。**

```
進入專案流程：
1. 閱讀 CODING_GUIDELINES.md（本文件，必讀）
2. 閱讀 memory/CLAUDE.md（專案規則）
3. 閱讀 memory/ARCHITECTURE.md（系統架構）
4. 閱讀 memory/HANDOFF.md（上次進度）
5. 閱讀 memory/TASKS.md（當前任務）
6. 開始執行任務
```

### 0.3 AI Agent 行為規範（Mandatory Directives）

| 規範 | 說明 |
|:---|:---|
| **先讀後寫（Read-Before-Write）** | 修改任何程式碼前，必須先讀取該模組及其 `README.md`，禁止憑記憶假設 |
| **禁止假設（No Assumptions）** | 禁止假設檔案路徑存在；操作前必須列出目錄確認 |
| **無聲修改禁止（No Silent Changes）** | 任何邏輯變動必須同步更新文件，無一例外 |
| **服務重啟確認** | 任何程式碼變更後，必須主動確認相關服務已重新載入，不可假設熱重載生效 |
| **Commit 紀律** | 每次成功驗證的變更，必須立即以 Conventional Commits 格式 commit |
| **環境衛生（Hygiene）** | 不留 `.bak`、`.tmp`、臨時測試檔；不留 `print()` 除錯語句；不留被大段註解掉的廢棄程式碼 |
| **防精簡協議 (Anti-Truncation Protocol)** | 嚴禁將終端機指令（如 `pip install`, `chmod`）、環境變數（`.env`）、或程式碼區塊精簡為摘要文字，必須 100% 保留其完整性與可複製性，絕對禁止刪除現有條文。 |
| **雙層文檔修改權限** | 嚴禁混修文檔。`docs/` (Root Docs) 專責環境部署與基礎設施引導；`open-claw-sandbox/docs/` (Sandbox Docs) 專責代碼規範與架構核心。 |

### 0.3.1 防精簡協議 (Anti-Truncation Protocol)

> **⚠️ 絕對鐵律：任何 AI Agent 在更新本專案文檔時，必須嚴格遵守以下防護機制，違者視為破壞系統完整性。**

1. **禁止濃縮終端機指令**：所有的安裝、部署、啟動腳本（如 `pip install`, `uvx`, `docker run`, `chmod`）必須以完整的 Markdown 程式碼區塊保留。不准將三行指令縮減為一句「請安裝依賴」。
2. **禁止假設環境設定**：不准假設使用者已經知道如何配置環境變數或啟動參數。所有的環境變數配置（例如 `launchctl setenv` 或 `.env` 檔案格式）必須 100% 保留。
3. **強制還原**：在執行文檔同步時，若發現前面的版本不慎將細節精簡成了摘要，你有義務主動從程式碼庫或記憶中提取完整資訊並將其**還原**，絕不允許繼承被閹割的資訊。

### 0.3.2 Single Source of Truth (SSoT) Documentation Strategy

> **Global Consolidation Protocol Activated**

The project has transitioned from a dual-layer documentation architecture to a unified **Single Source of Truth (SSoT)** under the `/docs/` directory. AI Agents must strictly adhere to this centralized structure:

- **Unified `/docs/` Directory**: This is the absolute SSoT for the Open Claw ecosystem. It encompasses all architectural decisions (`ARCHITECTURE.md`), operator manuals (`USER_MANUAL.md`), structural registries (`STRUCTURE.md`), coding guidelines (`CODING_GUIDELINES_FINAL.md`), and AI operational parameters (`AI_Master_Guide_Final.md`).
- **Deprecation of Sandbox Docs**: The `/open-claw-sandbox/docs/` directory is permanently deprecated. AI Agents must **never** create, read, or modify documentation within the sandbox directory.
- **Immutable Context Rule**: When updating these unified documents, you must maintain all historical contexts, terminal commands, and structural details to ensure full traceability and operational continuity.

### 0.4 原則優先順序

當原則之間發生衝突時：

```
安全性 > 正確性 > 可讀性 > 效能 > 簡潔性
```

---

## 1. 程式碼品質基礎原則

### 1.1 DRY — Don't Repeat Yourself

**定義：** 系統中每一份知識，都應該有唯一、明確、權威的表示。

**實踐：**
- 重複出現兩次以上的邏輯，立即抽出為函數或模組
- 重複出現的常數，集中定義在 `constants.py` 或 `config.ts`
- 重複的資料結構定義，抽出為共用型別

```python
# ❌ 錯誤示範
def get_user_greeting_en(name):
    return f"Hello, {name}! Welcome."

def get_user_greeting_zh(name):
    return f"你好, {name}！歡迎。"

# ✅ 正確示範
GREETINGS = {
    "en": "Hello, {name}! Welcome.",
    "zh": "你好, {name}！歡迎。"
}

def get_user_greeting(name: str, lang: str = "en") -> str:
    template = GREETINGS.get(lang, GREETINGS["en"])
    return template.format(name=name)
```

---

### 1.2 封裝（Encapsulation）

**定義：** 隱藏內部實作細節，只暴露必要的公開介面。

**實踐：**
- 內部函數使用 `_` 前綴（Python）或 `private` 關鍵字
- 模組只匯出真正需要被外部使用的部分
- 不讓外部直接修改內部狀態

```python
# ✅ 正確示範
class WeatherService:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key  # 私有，外部不能直接存取
        self._cache: dict = {}   # 私有實作細節

    def get_forecast(self, location: str) -> dict:
        """唯一對外介面"""
        if location in self._cache:
            return self._cache[location]
        return self._fetch_from_api(location)

    def _fetch_from_api(self, location: str) -> dict:
        """私有方法，外部不應直接呼叫"""
        ...
```

---

### 1.3 單一職責（Single Responsibility）

**定義：** 一個函數或類別，只做一件事，只有一個改變的理由。

**判斷標準：** 如果無法用一句話描述一個函數做什麼，它就太複雜了。

```python
# ❌ 錯誤示範 — 一個函數做太多事
def process_user_data(user):
    if not user.email:
        raise ValueError("Email required")
    user.name = user.name.strip().title()
    db.save(user)
    send_welcome_email(user.email)

# ✅ 正確示範 — 職責分離
def validate_user(user) -> None:
    if not user.email:
        raise ValueError("Email required")

def format_user(user) -> "User":
    user.name = user.name.strip().title()
    return user

def save_user(user) -> None:
    db.save(user)

def notify_new_user(user) -> None:
    send_welcome_email(user.email)
```

---

### 1.4 命名即文件

**定義：** 變數、函數、類別的命名，要讓人不看註解就能理解其用途。

**實踐：**
- 用完整單字，不用縮寫（除非是業界公認縮寫如 `id`、`url`）
- 函數名稱用動詞開頭
- 布林值用 `is_`、`has_`、`can_` 前綴

```python
# ❌ 不好的命名
def calc(d, r):
    return d * r / 100

# ✅ 好的命名
def calculate_discount_amount(original_price: float, discount_rate: float) -> float:
    return original_price * discount_rate / 100

is_user_active = True   # ✅
has_permission = False  # ✅
can_edit = True         # ✅
```

---

## 2. SOLID 原則

SOLID 是物件導向設計的五大核心原則，適用於任何有類別或模組概念的語言。

### 2.1 S — Single Responsibility Principle（單一職責）

見 [1.3 單一職責](#13-單一職責single-responsibility)

---

### 2.2 O — Open/Closed Principle（開放封閉原則）

**定義：** 對擴展開放，對修改封閉。新增功能時，應擴展現有程式碼，而非修改它。

```python
# ❌ 每次新增格式都要修改函數
def export_data(data, format_type):
    if format_type == "csv": ...
    elif format_type == "json": ...
    elif format_type == "xml":  # 新增時要修改函數
        ...

# ✅ 新增格式只需新增類別，不修改現有邏輯
class Exporter:
    def export(self, data): raise NotImplementedError

class CSVExporter(Exporter):
    def export(self, data): ...

class JSONExporter(Exporter):
    def export(self, data): ...

class XMLExporter(Exporter):  # 新增時不影響現有程式碼
    def export(self, data): ...
```

---

### 2.3 L — Liskov Substitution Principle（里氏替換原則）

**定義：** 子類別應該可以完全替換父類別，不破壞程式行為。

**實踐：**
- 子類別不應該縮減父類別的功能
- 子類別覆寫方法時，輸入輸出的型別和行為應保持相容

---

### 2.4 I — Interface Segregation Principle（介面隔離原則）

**定義：** 不強迫實作者依賴他們不需要的介面。介面要小而專。

```python
# ❌ 大介面，強迫實作不需要的方法
class DataProcessor:
    def read(self): ...
    def write(self): ...
    def delete(self): ...
    def send_email(self): ...  # 不是每個 Processor 都需要

# ✅ 小介面，各自獨立
class Readable:
    def read(self): ...

class Writable:
    def write(self): ...

class Notifiable:
    def send_email(self): ...
```

---

### 2.5 D — Dependency Inversion Principle（依賴反轉原則）

**定義：** 高層模組不應依賴低層模組；兩者都應依賴抽象。

```python
# ❌ 高層直接依賴具體實作
class ReportService:
    def __init__(self):
        self.db = MySQLDatabase()  # 直接依賴具體資料庫

# ✅ 依賴抽象介面
class Database:
    def query(self, sql): raise NotImplementedError

class ReportService:
    def __init__(self, db: Database) -> None:  # 依賴抽象
        self.db = db

# 使用時注入具體實作
service = ReportService(db=MySQLDatabase())
service = ReportService(db=PostgresDatabase())  # 輕鬆替換
```

---

## 3. 架構與設計原則

### 3.1 KISS — Keep It Simple, Stupid

**定義：** 能用簡單方式解決的，不要過度設計。

- 先讓程式跑起來，再考慮優化
- 不要為了「可能的未來需求」增加複雜度
- 簡單的程式更容易測試、維護、除錯

---

### 3.2 YAGNI — You Aren't Gonna Need It

**定義：** 不要實作現在不需要的功能。

- 不要預先寫「未來可能用到」的程式碼
- 需求到來時再實作，屆時你會有更多資訊做出更好的設計
- 過早抽象和過早優化一樣有害

---

### 3.3 關注點分離（Separation of Concerns）

**定義：** 不同的功能關注點，應該放在不同的模組中。

```
典型分層：
├── Presentation Layer   # UI / API 回應格式
├── Business Logic Layer # 核心業務邏輯
├── Data Access Layer    # 資料庫 / 外部 API 存取
└── Infrastructure Layer # 設定、日誌、認證
```

**實踐：**
- UI 層不直接存取資料庫
- 業務邏輯不包含 SQL 語句
- 資料層不包含業務規則

---

### 3.4 模組化（Modularity）

**定義：** 系統可以被拆開、獨立替換、獨立測試。

**實踐：**
- 每個模組有明確的輸入和輸出
- 模組之間透過定義好的介面溝通
- 可以替換一個模組而不影響其他模組

> **核心原則：** `skills/` 或 `apps/` 下的模組，不得互相引用。共用邏輯必須上移至 `core/` 或 `packages/`。

---

### 3.5 最小知識原則（Law of Demeter）

**定義：** 一個模組只應與直接相關的模組互動。

```python
# ❌ 違反最小知識原則（連鎖呼叫）
user.get_account().get_wallet().get_balance()

# ✅ 遵守最小知識原則
user.get_balance()  # User 自己封裝內部細節
```

---

### 3.6 適度抽象（Moderate Abstraction）

**定義：** 抽象程度要恰到好處，不過度也不不足。

| 層級 | 說明 | 問題 |
| ---- | ---- | ---- |
| 無抽象 | 直接寫二進位 / 低階操作 | 難以閱讀和維護 |
| 適度抽象 | 抽出核心邏輯、公開類別和方法 | ✅ 理想狀態 |
| 過度抽象 | 為了抽象而抽象，層層包裝 | 難以追蹤，過度工程化 |

---

### 3.7 減少全域依賴（Reduce Global Dependencies）

**定義：** 避免使用全域變數和全域狀態。

```python
# ❌ 全域狀態
current_user = None  # 全域變數，難以追蹤和測試

def get_user_name():
    return current_user.name

# ✅ 透過參數傳遞
def get_user_name(user: "User") -> str:
    return user.name
```

---

### 3.8 Design Patterns（設計模式）

適時使用設計模式，但不強求。三大類別：

| 類別 | 常用模式 | 適用場景 |
| ---- | -------- | -------- |
| **Creational（建立型）** | Factory, Singleton | 控制物件的建立方式 |
| **Structural（結構型）** | Adapter, Proxy | 組合物件和類別 |
| **Behavioral（行為型）** | Strategy, Observer | 定義物件之間的互動 |

> **原則：** 先識別問題，再找對應的模式；不要為了用模式而用模式。

---

## 4. 錯誤處理與防禦性程式設計

### 4.1 Fail Fast（快速失敗）

**定義：** 錯誤發生時立即中斷並報錯，不讓錯誤靜默擴散。

```python
# ❌ 靜默忽略錯誤
def get_config(key):
    try:
        return config[key]
    except:
        return None  # 靜默失敗，後續難以追蹤

# ✅ 明確失敗
def get_config(key: str) -> str:
    if key not in config:
        raise KeyError(
            f"Config key '{key}' not found. Available keys: {list(config.keys())}"
        )
    return config[key]
```

---

### 4.2 防禦性程式設計

**定義：** 永遠不信任外部輸入。

**外部輸入包括：**
- API 請求參數、使用者輸入、資料庫讀取結果
- 第三方 API 回應、環境變數

```python
def create_user(data: dict) -> "User":
    # 永遠驗證外部輸入
    if not isinstance(data.get("email"), str):
        raise ValueError("Email must be a string")
    if not re.match(r"[^@]+@[^@]+\.[^@]+", data["email"]):
        raise ValueError(f"Invalid email format: {data['email']}")
    if len(data.get("name", "")) > 100:
        raise ValueError("Name too long (max 100 chars)")
    ...
```

---

### 4.3 邊界情況（Edge Cases）

每個函數都必須考慮：

- **空值：** `None`、空字串、空陣列
- **極端值：** 超大數字、負數、零
- **編碼問題：** 中文、特殊字元、Emoji
- **並發情況：** 同時多個請求操作同一資源
- **網路問題：** 超時、斷線、回應格式異常

---

### 4.4 錯誤訊息規範

好的錯誤訊息應包含：

1. **發生了什麼**（What）
2. **在哪裡發生**（Where）
3. **如何修正**（How to fix）

```python
# ❌ 不好的錯誤訊息
raise Exception("Error")

# ✅ 好的錯誤訊息
raise ValueError(
    f"Invalid date format '{date_string}' in field 'start_date'. "
    f"Expected format: YYYY-MM-DD (e.g., 2024-01-15)"
)
```

---

### 4.5 錯誤嚴重度分級

| 方法 / 動作 | 使用時機 |
|---|---|
| `logger.info()` | 正常進度：階段開始、檔案寫入成功 |
| `logger.warning()` | 可恢復問題：跳過某檔案、正在重試 |
| `logger.error()` | 階段失敗：繼續處理下一個項目 |
| `raise RuntimeError(...)` | 不可恢復狀態：讓上層呼叫者處理 |

---

### 4.6 原子寫入原則（Atomic Write Principle）

**定義：** 防止程式中斷導致檔案毀損，所有持久化寫入必須遵循「先寫臨時檔，再重新命名」的策略。

```python
# ❌ 危險：程式中斷會留下損毀檔案
with open(path, "w") as f:
    f.write(content)

# ✅ 正確：原子寫入（write-then-rename）
import tempfile
import os

def atomic_write_text(path: str, content: str) -> None:
    """寫入臨時檔後重新命名，防止中斷損毀。"""
    dir_name = os.path.dirname(path)
    with tempfile.NamedTemporaryFile(
        mode="w", dir=dir_name, delete=False, suffix=".tmp"
    ) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    os.replace(tmp_path, path)  # 原子操作，成功或完全失敗
```

---

### 4.7 優雅關閉（Graceful Shutdown）

**定義：** 長時間運算的系統必須能正確處理中斷訊號。

**雙段式中斷行為：**
- **第一次 Ctrl+C**：完成當前工作後安全停止
- **第二次 Ctrl+C**：強制立即退出

```python
import signal

class MyOrchestrator:
    def __init__(self) -> None:
        self.stop_requested = False
        signal.signal(signal.SIGINT, self._handle_interrupt)

    def _handle_interrupt(self, signum, frame) -> None:
        if self.stop_requested:
            self.logger.error("💥 Second interrupt — forced exit.")
            os._exit(1)
        self.logger.warning("🚨 Interrupt received — will stop after current file.")
        self.stop_requested = True
```

---

### 4.8 Robustness（健壯性）

系統應能應對以下威脅而不崩潰：

| 威脅類型 | 應對策略 |
| -------- | -------- |
| Input Error（錯誤輸入） | 輸入驗證 + 清晰錯誤訊息 |
| Network Overload（網路過載） | Retry 機制 + Circuit Breaker |
| Disk Failure（磁碟故障） | 原子寫入 + 定期備份 |
| Intentional Attack（惡意攻擊） | 見安全原則章節 |

---

## 5. 可維護性原則

### 5.1 可讀性優先於聰明技巧

```python
# ❌ 聰明但難讀
result = [x**2 for x in range(10) if x % 2 == 0 and x > 0]

# ✅ 清晰易懂
even_positive_numbers = [x for x in range(10) if x % 2 == 0 and x > 0]
result = [number ** 2 for number in even_positive_numbers]
```

---

### 5.2 函數設計規範

- **函數要小：** 超過 20 行就考慮拆分
- **限制巢狀層數：** 超過 3 層立即重構（見第 18 章禁止模式）
- **參數不超過 3 個：** 超過 3 個改用物件傳入
- **避免 GOTO：** 製造不可追蹤的控制流

```python
# ❌ 參數過多
def create_event(title, date, time, location, description, is_public, max_attendees):
    ...

# ✅ 用物件包裝
from dataclasses import dataclass
from datetime import date, time as time_type

@dataclass
class EventData:
    title: str
    date: date
    time: time_type
    location: str
    description: str = ""
    is_public: bool = True
    max_attendees: int = 100

def create_event(event: EventData) -> "Event":
    ...
```

---

### 5.3 持續重構（Continuous Refactoring）

**定義：** 持續改善現有程式碼結構，不等到「爛掉」才動手。

**Boy Scout Rule：** 離開時讓程式碼比你進來時更乾淨。

**重構時機：**
- 新增功能前，先清理相關程式碼
- Code Review 發現問題時
- 函數超過 20 行時
- 出現重複程式碼時

---

### 5.4 文件與註解規範

**原則：** 註解說明「為什麼（Why）」，程式碼說明「做什麼（What）」。

```python
# ❌ 無意義的註解（程式碼已經說明了）
# 將 x 加 1
x = x + 1

# ❌ 過時的註解（比沒有更糟）
# 使用舊版 API（已更新但沒刪除此註解）
response = new_api.call()

# ✅ 有價值的註解（解釋為什麼）
# CWA API 的時間格式使用 HH:mm 字串比較，而非 timestamp
# 原因：API 回傳的時區不一致，字串比較更穩定
if current_time_str == forecast_time_str:
    ...
```

---

### 5.5 使用現代語言特性

- Python：使用 `type hints`、`dataclass`、`f-string`
- TypeScript：使用 `interface`、`type`、`enum`
- 不要為了相容舊版而拒絕使用新特性（除非有明確需求）

---

## 6. 測試原則

### 6.1 可測試性設計

**定義：** 設計時就考慮如何測試，而不是寫完再想。

**可測試的程式碼特徵：**
- 函數職責單一，易於隔離
- 依賴可以被注入（Dependency Injection）
- 沒有隱藏的全域狀態
- 輸入輸出明確

---

### 6.2 測試類型

| 類型 | 目的 | 速度 | 位置 |
| ---- | ---- | ---- | ---- |
| Unit Test | 測試單一函數邏輯 | 快 | `packages/*/tests/` |
| Integration Test | 測試模組間互動 | 中 | `tests/integration/` |
| E2E Test | 測試完整使用流程 | 慢 | `tests/e2e/` |

---

### 6.3 測試規範

- **測試覆蓋關鍵路徑**：不追求 100%，確保核心邏輯有保護
- **測試命名清晰**：`test_should_return_error_when_email_is_empty`
- **每個測試獨立**：測試之間不應互相依賴
- **測試要快**：Unit Test 應在毫秒級完成

```python
# ✅ 好的測試命名和結構
def test_should_raise_error_when_email_is_missing():
    # Arrange
    user_data = {"name": "Jinkun"}

    # Act & Assert
    with pytest.raises(ValueError, match="Email required"):
        validate_user(user_data)
```

---

## 7. 安全與效能原則

### 7.1 Security Assurance（安全保證）

#### SQL Injection 防護
```python
# ❌ 危險
query = f"SELECT * FROM users WHERE id = {user_id}"

# ✅ 使用參數化查詢
query = "SELECT * FROM users WHERE id = %s"
cursor.execute(query, (user_id,))
```

#### XSS 防護
- 永遠對輸出進行 HTML escape
- 使用框架內建的模板引擎，不手動拼接 HTML

#### Data Leakage 防護
- 日誌中不記錄敏感資訊（密碼、Token、個資）
- API 回應中不暴露系統內部資訊
- 錯誤訊息不包含 Stack Trace（生產環境）

---

### 7.2 最小權限原則（Least Privilege）

- 程式只申請它真正需要的權限
- 資料庫帳號只給必要的 CRUD 權限
- API Token 有效期限越短越好

---

### 7.3 敏感資訊管理

```bash
# ❌ 永遠不這樣做
API_KEY = "sk-1234567890abcdef"  # 硬寫在程式碼中

# ✅ 使用環境變數
API_KEY = os.environ.get("API_KEY")
if not API_KEY:
    raise EnvironmentError("API_KEY environment variable is required")
```

---

### 7.4 效能原則

- **過早優化是萬惡之源**：先讓程式正確，再根據實際瓶頸優化
- **量測後再優化**：使用 Profiler 找到真正的瓶頸
- **快取要有失效策略**：沒有失效策略的快取會造成資料不一致

---

## 8. 程式碼風格與格式

### 8.1 最重要的規則

> **符合現有 codebase 的風格，即使你個人不喜歡。一致性比個人偏好更重要。**

---

### 8.2 格式規範

| 項目 | 規範 |
| ---- | ---- |
| 縮排 | 4 個空格（Python），2 個空格（JS/TS），永不用 Tab |
| 行寬 | 最大 100 字元 |
| 空白行 | 邏輯區塊之間用空行隔開，並附上簡短說明 |
| 括號風格 | 全專案統一一種風格 |
| 行尾 | 統一使用 LF（Unix 換行） |
| 檔案結尾 | 最後一行保留空白行 |
| 編碼宣告 | `# -*- coding: utf-8 -*-` 放置於每個 `.py` 檔首行 |
| 字串引號 | 統一使用雙引號 `"`，單引號保留給內嵌字串 |
| 大數字 | 使用底線增加可讀性：`8_000`、`30_000` |

---

### 8.3 `.editorconfig`（跨編輯器統一）

在專案根目錄放置此文件，確保所有編輯器和 AI 工具行為一致：

```ini
root = true

[*]
indent_style = space
indent_size = 2
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true

[*.py]
indent_size = 4

[*.md]
trim_trailing_whitespace = false
```

---

### 8.4 語言專屬規範

| 語言 | 規範工具 | 設定檔 |
| ---- | -------- | ------ |
| Python | Ruff + mypy | `pyproject.toml` |
| TypeScript | ESLint + Prettier | `.eslintrc.json` + `.prettierrc` |
| JavaScript | ESLint + Prettier | 同上 |

---

### 8.5 Console Output 日誌慣例

使用一致的 emoji 前綴區分輸出嚴重程度：

| Emoji | 意義 |
|:---:|:---|
| `✅` | Success — 任務成功完成 |
| `⚠️` | Warning — 可恢復問題，繼續執行 |
| `❌` | Error — 任務失敗，繼續下一個 |
| `🔄` | In progress — 正在執行 |
| `⏸️` | Paused — 等待使用者輸入 |
| `🚨` | Critical — 優雅關閉啟動 |
| `💥` | Fatal — 硬體緊急強制退出 |

---

## 9. 函數編寫完美主義細則

> 本章定義函數層級的最高標準，源自實作版「The Antigravity Perfectionist Code」。

### 9.1 Type Annotations（型別標注）

所有**公開函數和方法**必須有完整的型別標注。

```python
# ✅ 完整標注
def run(self, subject: str, filename: str, force: bool = False) -> bool: ...

# ✅ __init__ 永遠回傳 None
def __init__(self) -> None: ...

# ✅ Optional 參數
from typing import Optional, Dict, List, Tuple
def load_checkpoint(self) -> Optional[Dict[str, str]]: ...

# ✅ 前向引用用字串
@classmethod
def from_config(cls, path: str) -> "MyClass": ...
```

**嚴禁使用 `Any`，除非對接無型別定義的第三方套件，且必須加上說明：**

```python
# ❌
from typing import Any
def process(self, data: Any) -> Any: ...

# ✅ 若真的無法避免，必須說明原因
from typing import Any
def parse_legacy_api(self, raw: Any) -> "ParsedResult":
    # raw 來自無型別定義的舊版 SDK，型別不可控
    ...
```

---

### 9.2 視覺間隔與區塊標注

不同的邏輯區塊之間必須用單行空行隔開，並配上簡短說明：

```python
# ✅ 正確：邏輯分區清晰
def process_document(self, path: str) -> bool:
    # ── 1. 讀取與驗證 ─────────────────────────────────────────
    if not os.path.exists(path):
        self.logger.error(f"❌ File not found: {path}")
        return False

    # ── 2. 核心處理 ───────────────────────────────────────────
    content = self._read_file(path)
    result = self._transform(content)

    # ── 3. 寫入輸出 ───────────────────────────────────────────
    output_path = os.path.join(self.output_dir, os.path.basename(path))
    atomic_write_text(output_path, result)

    return True
```

---

### 9.3 Docstring 規範（Google Style）

所有公開類別和非顯而易見的公開方法，必須有 Google Style 的 docstring。

#### 方法 Docstring

```python
def run(self, subject: str, filename: str, force: bool = False) -> bool:
    """
    執行主處理流程。

    Args:
        subject: 資料夾名稱，對應 data/input/<subject>/。
        filename: 要處理的檔案名稱。
        force: 若為 True，即使已處理過也重新執行。

    Returns:
        True 表示成功，False 表示失敗（已記錄到 logger）。

    Raises:
        不拋出例外，所有錯誤透過回傳值和 logger 處理。
    """
```

#### 禁止寫的 Docstring

```python
# ❌ 重述顯而易見的內容
def get_file_hash(self, filepath: str) -> str:
    """Get the file hash."""
    ...

# ❌ 對非顯然的公開方法不寫 Docstring
def ensure_directories(self) -> None:
    for path in [...]:
        os.makedirs(path, exist_ok=True)
```

---

### 9.4 類別內部結構順序

同一個類別內，各成員依照以下固定順序排列：

```python
class MyClass:
    # 1. 類別層級常數
    MAX_RETRIES = 3
    TIMEOUT_MS  = 30_000

    # 2. __init__
    def __init__(self, ...) -> None: ...

    # 3. 類別方法與靜態方法
    @classmethod
    def from_config(cls, path: str) -> "MyClass": ...

    @staticmethod
    def _validate(value: str) -> bool: ...

    # 4. 公開屬性（@property）
    @property
    def name(self) -> str: ...

    # 5. 公開方法（同一邏輯群組內依字母排序）
    def diff_files(self, ...) -> "DiffResult": ...
    def write_html(self, ...) -> str: ...

    # 6. 私有方法（_ 前綴）
    def _build_html(self, ...) -> str: ...
    def _resolve(self, rel: str) -> str: ...

    # 7. __repr__ 和 __str__ 最後
    def __repr__(self) -> str: ...
```

---

### 9.5 資料結構：Dataclass 優先

使用 dataclass 取代裸字典作為函數回傳值：

```python
# ✅ 型別安全、自文件化
from dataclasses import dataclass

@dataclass
class ProcessResult:
    file_path:  str
    char_count: int
    success:    bool = True
    error:      str = ""

def process_file(self, path: str) -> ProcessResult:
    result = ProcessResult(file_path=path, char_count=0)
    ...
    return result

# ❌ 不透明，型別不安全
def process_file(self, path):
    return {"path": path, "chars": 0, "ok": True}
```

---

### 9.6 常數與魔法值

所有「魔法數字」或「魔法字串」必須定義為具名常數：

```python
# ✅
MIN_RETENTION_RATIO = 0.30   # 內容保留率下限，低於此值視為處理失敗
DEBOUNCE_SECONDS    = 3.0    # 等待檔案複製完成的防抖時間

if retention_ratio < MIN_RETENTION_RATIO:
    ...

# ❌
if retention_ratio < 0.30:
    ...
```

---

### 9.7 Import 順序

```python
# Group 1 — 標準函式庫
import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Group 2 — 第三方套件
import psutil
import yaml

# Group 3 — 專案內部模組
from core import PipelineBase, AtomicWriter
from core.diff_engine import DiffEngine
```

**規則：**
- 永遠不使用萬用字元匯入：`from module import *`
- 永遠不在函數體內匯入（除非避免循環依賴）

---

## 10. 命名規範

### 10.1 命名風格

| 風格 | 格式 | 適用場景 |
| ---- | ---- | -------- |
| `camelCase` | `variableName` | JS/TS 變數和函數 |
| `PascalCase` | `ClassName` | 類別（各語言通用）、React 元件 |
| `snake_case` | `variable_name` | Python 變數和函數 |
| `UPPER_SNAKE_CASE` | `CONSTANT_NAME` | 常數 |
| `kebab-case` | `file-name` | 檔案名稱、URL |

---

### 10.2 命名規則

```
✅ 好的命名：
- 完整單字：calculate_discount（而非 calc_disc）
- 動詞開頭（函數）：get_user、send_notification、validate_input
- 名詞（類別）：UserService、WeatherBot、DatabaseConnection
- is/has/can 開頭（布林）：is_active、has_permission、can_delete
- 陣列用複數：users、event_logs、api_keys

❌ 不好的命名：
- 單字母：x、i（除了迴圈計數器）
- 縮寫：usr、evt、btn（除非業界通用）
- 模糊名稱：data、info、temp、stuff
- 誤導名稱：is_valid 實際上修改資料
```

---

### 10.3 檔案命名規範

| 類型 | 規範 | 範例 |
| ---- | ---- | ---- |
| 一般程式檔 | `kebab-case` | `weather-service.py` |
| 類別檔案 | `PascalCase` 或 `kebab-case` | `WeatherService.py` |
| 測試檔案 | `test_` 前綴 或 `.test.` | `test_weather.py` / `weather.test.ts` |
| 設定檔 | 小寫或 `.` 開頭 | `config.yaml` / `.env` |
| 手冊文件 | 全大寫 | `README.md` / `CLAUDE.md` |
| 型別定義 | `types.` 或 `.d.ts` | `types.py` / `api.d.ts` |
| 常數檔案 | `constants.` 開頭 | `constants.py` |

---

### 10.4 Open Claw Workspace 命名規範

> 此節為 Open Claw Workspace 的唯一命名法則來源。

| 適用範疇 | 命名法則 | 範例 |
|:---|:---|:---|
| **資料目錄** (`data/<skill>/`) | `lower_snake_case` | `input`, `01_processed`, `error` |
| **Skill 目錄** (`skills/`) | `kebab-case` | `doc-parser`, `audio-transcriber` |
| **Core 模組檔案** | `snake_case` | `pipeline_base.py`, `log_manager.py` |
| **Phase 腳本檔案** | `snake_case` + 相位前綴 | `p01a_engine.py`, `p02_highlight.py` |
| **Python 類別** | `PascalCase` | `Phase1aPDFEngine`, `ResumeManager` |
| **Python 函數 / 方法** | `snake_case` | `run()`, `save_checkpoint()` |
| **Python 常數** | `UPPER_SNAKE_CASE` | `MIN_RETENTION_RATIO` |
| **Config / YAML 鍵值** | `snake_case` | `timeout_seconds`, `chunk_size` |
| **系統文件** | `UPPER_SNAKE_CASE` | `CODING_GUIDELINES.md`, `SKILL.md` |
| **環境變數** | `UPPER_SNAKE_CASE` | `WORKSPACE_DIR`, `HF_HOME` |
| **Git 分支** | `kebab-case` | `feature/session-state`, `fix/log-verbosity` |

---

## 11. 專案結構標準

### 11.1 功能目錄分層原則

| 目錄 | 職責 |
|---|---|
| `core/` | 不依賴外部業務、可跨模組共用的底層邏輯 |
| `skills/` | 具體任務模組，每個 Skill 必須獨立、可測試、不跨 Skill 引用 |
| `apps/` | 各子系統的對外接口（API、Bot、Web 前端） |
| `packages/` | 跨子系統共用的業務模組 |
| `ops/` | 自動化腳本（如 `check.sh`）、一次性操作腳本，用完刪除 |
| `docs/` | 對外文件（開源用） |
| `memory/` | AI 協作記憶體系統 |
| `tests/` | E2E 與跨模組整合測試 |

> **核心原則：`skills/` 或 `apps/` 下的模組，不得互相引用。共用邏輯必須上移至 `core/` 或 `packages/`。**

---

### 11.2 Monorepo 完整結構

```
my-project/
│
├── .github/                        # GitHub 相關設定
│   ├── workflows/
│   │   ├── test.yml
│   │   ├── lint.yml
│   │   └── deploy.yml
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
│
├── apps/                           # 各子系統（可獨立運行）
│   ├── api/                        # 對外 REST/GraphQL API
│   ├── telegram-bot/               # Telegram 接入層
│   ├── web/                        # Web 前端（若有）
│   └── worker/                     # 背景排程 / 自動化任務
│
├── packages/                       # 跨子系統共用模組
│   ├── core/                       # 核心業務邏輯
│   ├── db/                         # 資料庫 schema + 存取層
│   ├── types/                      # 共用型別定義
│   └── utils/                      # 通用工具函數
│
├── infra/                          # 基礎設施設定
│   ├── docker/
│   ├── nginx/
│   └── scripts/
│
├── docs/                           # 對外文件（開源用）
│   ├── api/
│   │   ├── openapi.yaml
│   │   ├── VERSIONING.md
│   │   ├── RATE_LIMITING.md
│   │   └── AUTH.md
│   ├── architecture/
│   └── guides/
│
├── memory/                         # AI 協作記憶體系統
│   ├── CLAUDE.md
│   ├── HANDOFF.md
│   ├── TASKS.md
│   ├── DECISIONS.md
│   └── ARCHITECTURE.md
│
├── ops/                            # 自動化檢查腳本（用完刪除）
│   └── check.sh
│
├── tests/                          # 全域測試
│   ├── e2e/
│   └── integration/
│
├── .env.example
├── .gitignore
├── .editorconfig
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SECURITY.md
├── LICENSE
└── pyproject.toml / package.json
```

---

### 11.3 子模組內部結構規範

```
module/
├── src/
│   ├── __init__.py 或 index.ts    # 公開介面（只匯出需要的）
│   ├── constants.py               # 常數定義
│   ├── types.py                   # 型別定義
│   ├── utils.py                   # 工具函數
│   └── [功能模組]/
├── tests/
│   ├── unit/
│   └── integration/
├── README.md
└── requirements.txt 或 package.json
```

---

## 12. 手冊文件體系（Human + AI 雙軌）

### 12.1 文件分層架構

```
文件體系
├── AI 讀取層（memory/）          # AI Agent 優先讀取
├── Human 協作層（根目錄）         # 團隊成員讀取
└── API 文件層（docs/api/）        # 外部使用者讀取
```

---

### 12.2 AI 讀取層（`memory/`）

> 所有 AI Agent 進入專案時**必須按順序閱讀**此目錄下的文件。

| 檔案 | 用途 | 更新時機 | 負責人 |
| ---- | ---- | -------- | ------ |
| `CLAUDE.md` | 專案規則、AI 行為準則、禁止事項 | 規則改變時 | 專案負責人 |
| `HANDOFF.md` | 上次做到哪、下次從哪開始、未解決問題 | 每次 session 結束時 | 最後工作者 |
| `TASKS.md` | 待辦、進行中、已完成任務 | 每次任務狀態變動 | 當前工作者 |
| `DECISIONS.md` | 為什麼選這個技術或架構的決策記錄 | 重大決策後 | 決策者 |
| `ARCHITECTURE.md` | 系統全貌、資料流、模組關係圖 | 架構變動時 | 架構負責人 |

#### `CLAUDE.md` 範本結構

```markdown
# 專案名稱

## 專案概述
（一段話描述此系統做什麼）

## 技術棧
- 語言：
- 框架：
- 資料庫：
- 部署：

## AI Agent 行為規則
- 修改任何程式碼前必須先閱讀相關模組的 README
- 不得修改 .env 和任何包含真實憑證的檔案
- 每次 session 結束前必須更新 HANDOFF.md
- 新增功能前先確認 TASKS.md 中的優先順序

## 禁止事項
- 不得直接推送到 main branch
- 不得刪除任何帶有 [KEEP] 標記的程式碼
- 不得更改資料庫 schema 而不同時更新 migration

## 目前狀態
（系統目前的健康狀況）
```

#### `HANDOFF.md` 範本結構

```markdown
# Handoff 記錄

## 最後更新
- 日期：YYYY-MM-DD
- 工作者：（姓名或 AI Agent 名稱）

## 已完成
- [ ] 任務描述

## 進行中
- [ ] 任務描述（完成 X%）
  - 目前進度：
  - 下一步：

## 待解決問題
- 問題描述（Priority: High/Medium/Low）

## 注意事項
（下一位工作者需要知道的事）
```

#### `TASKS.md` 範本結構

```markdown
# 任務清單

## 🔴 High Priority
- [ ] 任務描述

## 🟡 Medium Priority
- [ ] 任務描述

## 🟢 Low Priority
- [ ] 任務描述

## ✅ 已完成
- [x] 任務描述（完成日期）
```

#### `DECISIONS.md` 範本結構

```markdown
# 決策記錄

## [YYYY-MM-DD] 決策標題

### 背景
（為什麼需要做這個決策）

### 選項
1. 選項 A：優點... 缺點...
2. 選項 B：優點... 缺點...

### 決定
選擇了選項 A，原因：...

### 後果
（這個決策帶來的影響）
```

---

### 12.3 Human 協作層（根目錄）

| 檔案 | 用途 | 必要性 |
| ---- | ---- | ------ |
| `README.md` | 專案介紹、快速啟動、徽章 | ✅ 必要 |
| `CONTRIBUTING.md` | 如何貢獻程式碼、PR 流程 | 小團隊起開始 |
| `CHANGELOG.md` | 每個版本做了什麼（語意版本） | ✅ 必要 |
| `LICENSE` | 授權聲明 | 開源前必要 |
| `SECURITY.md` | 如何回報安全漏洞 | 多人協作起開始 |
| `CODE_OF_CONDUCT.md` | 社群行為準則 | 開源前必要 |

---

### 12.4 API 文件層（`docs/api/`）

| 檔案 | 用途 |
| ---- | ---- |
| `openapi.yaml` | OpenAPI 3.0 規格定義（機器可讀） |
| `VERSIONING.md` | 版本策略（v1/v2 升版規則） |
| `RATE_LIMITING.md` | 限流規則、配額說明 |
| `AUTH.md` | 認證方式、Token 申請流程 |

---

## 13. Git 版本控制規範

### 13.1 Branch 命名

```
main              # 穩定版，永遠可部署，受保護
develop           # 開發主線，整合測試後合併到 main
feature/xxx       # 新功能（e.g., feature/telegram-weather-alert）
fix/xxx           # 修 bug（e.g., fix/api-null-response）
docs/xxx          # 純文件更新
refactor/xxx      # 重構，不改功能
test/xxx          # 補測試
chore/xxx         # 工具、設定、依賴更新
release/vX.Y.Z    # 發版準備
hotfix/xxx        # 緊急修復生產環境 bug
```

---

### 13.2 Commit 訊息規範（Conventional Commits）

```
格式：<type>(<scope>): <description>

type 類型：
  feat     新功能
  fix      修 bug
  docs     文件更新
  refactor 重構（不改功能）
  test     新增或修改測試
  chore    工具、設定、依賴
  perf     效能優化
  style    程式碼格式（不影響邏輯）

範例：
  feat(telegram-bot): 新增即時天氣推播功能
  fix(api): 修正回傳空值時的 500 錯誤
  docs(readme): 更新安裝步驟
  refactor(weather): 將 API 呼叫抽出為獨立服務
  test(auth): 新增 JWT 驗證單元測試
  chore(deps): 更新 requests 至 2.31.0
```

---

### 13.3 PR（Pull Request）規範

- PR 只做一件事
- PR 描述說明「為什麼」這樣改
- 合併前必須通過 CI 測試
- 至少一位 reviewer 批准（小團隊起）
- 使用 Squash Merge 保持 main branch 歷史清晰

---

### 13.4 `.gitignore` 必要項目

```gitignore
# 環境變數（絕對不提交）
.env
.env.local
.env.production
.env.*
!.env.example

# 依賴
node_modules/
__pycache__/
*.pyc
.venv/
venv/

# 編譯產物
dist/
build/
*.egg-info/

# IDE 設定
.vscode/
.idea/
*.swp

# 系統檔案
.DS_Store
Thumbs.db

# 測試覆蓋率報告
.coverage
htmlcov/
coverage/

# 日誌
*.log
logs/
```

---

## 14. 環境變數與設定管理

### 14.1 三層環境設定

```
環境層級：
├── .env.example     # ✅ 提交到 git（範本，無真實值）
├── .env.local       # ❌ 不提交（本機開發用）
├── .env.test        # ❌ 不提交（測試環境）
└── .env.production  # ❌ 不提交（走 CI/CD secrets）
```

---

### 14.2 `.env.example` 標準格式

```bash
# ================================
# 應用程式設定
# ================================
APP_NAME=my-project
APP_ENV=development          # development | staging | production
APP_PORT=3000
APP_SECRET_KEY=              # 必填：openssl rand -hex 32

# ================================
# 資料庫
# ================================
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# ================================
# Telegram Bot
# ================================
TELEGRAM_BOT_TOKEN=          # 必填：從 @BotFather 取得

# ================================
# 外部 API
# ================================
CWA_API_KEY=                 # 中央氣象署 API Key
GEMINI_API_KEY=              # Google Gemini API Key
```

---

### 14.3 讀取環境變數規範

```python
import os
from dotenv import load_dotenv

load_dotenv()

# ✅ 必填變數：找不到就報錯
def get_required_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. "
            f"See .env.example for reference."
        )
    return value

# ✅ 選填變數：有預設值
APP_PORT = int(os.environ.get("APP_PORT", "3000"))

# ✅ 必填變數
DATABASE_URL = get_required_env("DATABASE_URL")
TELEGRAM_BOT_TOKEN = get_required_env("TELEGRAM_BOT_TOKEN")
```

---

## 15. API 設計規範

### 15.1 版本控制

```
URL 路徑版本：
  /api/v1/users
  /api/v2/users

版本升版規則：
  - Patch（v1.0.X）：Bug fix，不影響介面
  - Minor（v1.X.0）：向後相容的新功能
  - Major（vX.0.0）：破壞性變更，需提前通知
```

---

### 15.2 REST API 命名規範

```
✅ 資源用名詞複數：
  GET    /api/v1/users           # 取得清單
  POST   /api/v1/users           # 建立
  GET    /api/v1/users/{id}      # 取得單一
  PUT    /api/v1/users/{id}      # 完整更新
  PATCH  /api/v1/users/{id}      # 部分更新
  DELETE /api/v1/users/{id}      # 刪除

✅ 巢狀資源：
  GET    /api/v1/users/{id}/posts

❌ 不用動詞：
  /api/v1/getUsers       # 錯誤
  /api/v1/createUser     # 錯誤
```

---

### 15.3 回應格式標準

```json
{
  "success": true,
  "data": { "..." : "..." },
  "meta": {
    "page": 1,
    "total": 100,
    "version": "v1"
  }
}
```

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Email format is invalid",
    "field": "email"
  }
}
```

---

### 15.4 HTTP 狀態碼規範

| 狀態碼 | 用途 |
| ------ | ---- |
| 200 | 成功 |
| 201 | 建立成功 |
| 204 | 成功但無回應內容（刪除） |
| 400 | 請求格式錯誤 |
| 401 | 未認證 |
| 403 | 無權限 |
| 404 | 資源不存在 |
| 422 | 驗證失敗 |
| 429 | 請求過於頻繁（Rate Limit） |
| 500 | 伺服器內部錯誤 |

---

## 16. 自動化強制工具鏈

> 本章指定具體工具，讓準則具備「強制性」而非僅是「建議性」。

### 16.1 Linter / Formatter — Ruff

所有 Python 程式碼必須通過 `ruff check` 與 `ruff format`，零警告。

**安裝：**
```bash
pip install ruff
```

**專案設定（`pyproject.toml`）：**
```toml
[tool.ruff]
target-version = "py39"
line-length = 100

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort（import 排序）
    "N",    # pep8-naming
    "UP",   # pyupgrade（現代 Python 語法）
    "B",    # flake8-bugbear（常見 bug）
    "C4",   # flake8-comprehensions
    "SIM",  # flake8-simplify
    "RUF",  # ruff 專屬規則
]
ignore = [
    "E501",  # 行長由 ruff format 處理
]

[tool.ruff.lint.isort]
known-first-party = ["core"]
force-sort-within-sections = true
```

**執行：**
```bash
ruff check .          # 檢查所有 Python 檔案
ruff check --fix .    # 自動修復安全問題
ruff format .         # 格式化（相容 Black）
```

---

### 16.2 Static Type Checker — Mypy

**安裝：**
```bash
pip install mypy
```

**設定（`pyproject.toml`）：**
```toml
[tool.mypy]
python_version = "3.9"
strict = false
disallow_untyped_defs = true    # 所有公開方法必須有型別標注
warn_return_any = true
warn_unused_ignores = true
ignore_missing_imports = true
```

**執行：**
```bash
mypy core/   # 針對核心模組執行型別檢查
```

---

### 16.3 Pre-commit Hooks

**安裝：**
```bash
pip install pre-commit
```

**`.pre-commit-config.yaml`：**
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-merge-conflict
      - id: debug-statements       # 攔截殘留的 breakpoint() / pdb
```

**啟用：**
```bash
pre-commit install           # 安裝 hook
pre-commit run --all-files   # 立即對所有檔案執行一次
```

---

### 16.4 VS Code 標準配置

**`.vscode/extensions.json`：**
```json
{
  "recommendations": [
    "charliermarsh.ruff",
    "ms-python.mypy-type-checker",
    "ms-python.python",
    "redhat.vscode-yaml",
    "yzhang.markdown-all-in-one"
  ]
}
```

**`.vscode/settings.json`：**
```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "charliermarsh.ruff",
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": "explicit",
      "source.organizeImports.ruff": "explicit"
    }
  },
  "python.analysis.typeCheckingMode": "basic",
  "files.trimTrailingWhitespace": true,
  "files.insertFinalNewline": true
}
```

---

### 16.5 全部檢查一鍵執行（`ops/check.sh`）

```bash
#!/usr/bin/env bash
set -euo pipefail

echo "🔍 Ruff lint..."
ruff check .

echo "🎨 Ruff format check..."
ruff format --check .

echo "🔬 Mypy (core only)..."
mypy core/

echo "✅ All checks passed"
```

```bash
chmod +x ops/check.sh
./ops/check.sh
```

---

## 17. 各階段啟用原則

### 階段一：單人開發

**啟用：**
- `memory/` 目錄完整建立
- `README.md` + `.env.example`
- Git branch 規範（main + feature branches）
- Conventional Commits
- `.editorconfig` + `.gitignore`
- Ruff + Mypy 基本設定
- 基本 Unit Test

---

### 階段二：小團隊（2–5 人）

**新增：**
- `CONTRIBUTING.md`
- `CHANGELOG.md`
- GitHub Actions（自動測試 + Lint）
- PR Template + 至少 1 位 reviewer
- Issue Templates
- `SECURITY.md`
- Pre-commit hooks
- Integration Tests

---

### 階段三：多人協作

**新增：**
- `docs/api/` 完整建立
- OpenAPI 規格文件
- Code Review Checklist
- Branch Protection Rules（不可直接推 main）
- 自動化部署（CD）
- 效能監控 / 錯誤追蹤（Sentry 等）

---

### 階段四：開源

**新增：**
- `LICENSE`（選擇授權：MIT / Apache 2.0 / GPL）
- `CODE_OF_CONDUCT.md`
- Release workflow（自動打 tag + 發布 CHANGELOG）
- 完整 `docs/guides/`
- 貢獻者感謝機制

---

## 18. 禁止模式（Prohibited Patterns）

> 本章是強制性底線，非建議。所有開發者（Human & AI）均須遵守。

### 18.1 禁止模式速查表

| 禁止行為 | 強制替代方案 |
|---|---|
| `global` 變數（除 Constants 外） | 透過參數傳遞或依賴注入 |
| `print()` 除錯語句 | `logger.info()` / `logger.debug()` |
| 空的 `except: pass` | 記錄至 `logger.error()` 並回傳失敗指標 |
| 邏輯巢狀超過 3 層 | 抽出為獨立函數或提前 return |
| 硬寫路徑字串 | 透過 config / 環境變數解析 |
| 函數內 import（除避免循環依賴外） | 移至檔案頂部 |
| 萬用字元匯入：`from x import *` | 明確列出需要的名稱 |
| 無型別標注的公開函數 | 加上完整 type hints |
| 裸字典作為函數回傳值 | 使用 `@dataclass` |
| 魔法數字 / 魔法字串直接寫在邏輯中 | 定義為具名常數 |
| 一次 commit 塞入多個無關改動 | 一次 commit 只做一件事 |
| 保留 `.bak`、`.tmp` 等垃圾檔案 | 立即刪除 |
| 無聲修改程式碼不更新文件 | 所有邏輯變動必須同步更新文件 |
| 直接複寫重要檔案 | 使用原子寫入策略（write-then-rename） |

---

### 18.2 禁止：Print 語句

```python
# ❌ 嚴禁
print(f"Processing {filename}...")
print("Error occurred!")

# ✅ 使用 logger
import logging
logger = logging.getLogger(__name__)

logger.info(f"✅ Processing {filename}...")
logger.error(f"❌ Failed to process {filename}: {e}")
```

---

### 18.3 禁止：吞掉異常

```python
# ❌ 嚴禁
try:
    result = process(data)
except:
    pass

# ✅ 正確：記錄錯誤，回傳明確的失敗指標
try:
    result = process(data)
except Exception as e:
    logger.error(f"❌ process() failed for {data}: {e}")
    return False
```

---

### 18.4 禁止：過度巢狀（超過 3 層）

```python
# ❌ 超過 3 層巢狀，難以閱讀和測試
def process(items):
    for item in items:
        if item.is_valid():
            for sub in item.children:
                if sub.active:
                    for record in sub.records:
                        if record.date > cutoff:
                            save(record)

# ✅ 提早 return / 抽出子函數
def process(items):
    for item in items:
        if not item.is_valid():
            continue
        _process_item(item)

def _process_item(item):
    for sub in item.children:
        if sub.active:
            _process_sub(sub)

def _process_sub(sub):
    for record in sub.records:
        if record.date > cutoff:
            save(record)
```

---

### 18.5 Code Review Checklist

每次 PR 或重大改動，在合併前必須自行對照此清單：

#### 架構層面
- [ ] 新程式碼不跨 skill / app 邊界直接引用
- [ ] 共用邏輯已上移至 `core/` 或 `packages/`
- [ ] `core/` 改動向後相容

#### 程式碼品質
- [ ] `ruff check` 零警告
- [ ] `ruff format` 無差異（已格式化）
- [ ] 所有公開方法有完整型別標注
- [ ] 所有公開類別和非顯然方法有 Google Style docstring
- [ ] 所有魔法值已定義為具名常數
- [ ] 無 `except: pass` 或靜默吞例外
- [ ] 涉及檔案寫入處使用原子寫入策略

#### 文件同步
- [ ] `README.md` 或 `ARCHITECTURE.md` 已更新（若行為有變）
- [ ] `DECISIONS.md` 已更新（若有非顯然的設計選擇）
- [ ] `CODING_GUIDELINES.md` 已更新（若引入新模式）

---

## 19. 快速參考總表

### 原則速查

| 類別 | 原則 | 一句話說明 |
| ---- | ---- | ---------- |
| 程式碼品質 | DRY | 不重複 |
| 程式碼品質 | 封裝 | 隱藏細節，暴露介面 |
| 程式碼品質 | SRP | 一個函數只做一件事 |
| 程式碼品質 | 命名即文件 | 看名字就知道做什麼 |
| SOLID | S | 單一職責 |
| SOLID | O | 擴展開放，修改封閉 |
| SOLID | L | 子類別可替換父類別 |
| SOLID | I | 介面要小而專 |
| SOLID | D | 依賴抽象，不依賴具體 |
| 架構 | KISS | 保持簡單 |
| 架構 | YAGNI | 不預先寫不需要的功能 |
| 架構 | 關注點分離 | UI / 邏輯 / 資料各自獨立 |
| 架構 | 模組化 | 可拆開、可替換、可獨立測試 |
| 架構 | 最小知識 | 只跟直接相關的互動 |
| 架構 | 適度抽象 | 不過度也不不足 |
| 架構 | 減少全域依賴 | 用參數傳遞，不用全域變數 |
| 錯誤 | Fail Fast | 錯了就立刻停 |
| 錯誤 | 防禦性 | 永遠驗證外部輸入 |
| 錯誤 | 原子寫入 | 防止中斷損毀檔案 |
| 錯誤 | 優雅關閉 | 雙段中斷，安全停止 |
| 錯誤 | Robustness | 面對威脅不崩潰 |
| 維護 | 可讀性 > 聰明 | 寫給人看，不是寫給機器看 |
| 維護 | 持續重構 | 邊走邊清，不等爛掉 |
| 維護 | 文件說 Why | 程式碼說 What，文件說 Why |
| 測試 | 可測試性 | 設計時就考慮測試 |
| 測試 | 覆蓋關鍵路徑 | 不追求 100%，保護核心邏輯 |
| 安全 | 最小權限 | 只申請必要權限 |
| 安全 | 不硬寫密鑰 | 走環境變數 |
| 安全 | 防 SQL Injection | 用參數化查詢 |
| 效能 | 不過早優化 | 先正確，再優化 |
| 效能 | 量測後再優化 | 用數據決定優化點 |

---

### 工具速查

| 工具 | 用途 | 執行指令 |
|---|---|---|
| Ruff | Linting + Formatting | `ruff check . && ruff format .` |
| Mypy | 靜態型別檢查 | `mypy core/` |
| pre-commit | Commit 前自動門禁 | `pre-commit install` |
| ops/check.sh | 一鍵全部檢查 | `./ops/check.sh` |

---

### 文件速查

| 文件 | 主要讀者 | 更新頻率 |
| ---- | -------- | -------- |
| `memory/CLAUDE.md` | AI Agent | 規則改變時 |
| `memory/HANDOFF.md` | AI Agent + 下一位工作者 | 每次 session |
| `memory/TASKS.md` | AI Agent + 當前工作者 | 每日 |
| `memory/DECISIONS.md` | AI Agent + 全團隊 | 重大決策後 |
| `memory/ARCHITECTURE.md` | AI Agent + 全團隊 | 架構變動時 |
| `README.md` | 新成員 + 外部使用者 | 功能更新時 |
| `CONTRIBUTING.md` | 貢獻者 | 流程改變時 |
| `CHANGELOG.md` | 使用者 + 團隊 | 每次發版 |
| `docs/api/openapi.yaml` | API 使用者 + AI Agent | API 變動時 |

---

## 20. 版本演進與背景記錄

### v1.0.0（2026-04-17）—— 初版建立

**核心開發與品質原則：**
- **08:40 AM**：確立封裝、DRY 與操作規範為核心。
- **08:47 AM**：定義 DRY、封裝、SRP 與「命名即文件」作為品質基礎。確立 SOLID 五大原則，引入 KISS、YAGNI、最小知識原則。
- **09:06 AM**：細化「適度抽象」與「減少全域依賴」；整合 SQL 注入與 XSS 防護規範；確立 Human + AI 雙軌文件體系。

### v1.1.0（2026-04-17）—— 工程加固版

整合實作版（v3.1）缺漏補強，強化工業級安全與可靠性：

- **新增 §4.6**：原子寫入原則（Atomic Write Principle），防止程式中斷損毀檔案。
- **新增 §4.7**：優雅關閉（Graceful Shutdown），定義雙段式中斷行為。
- **新增 §9**：函數編寫完美主義細則，整合 Type Annotations、Google Style Docstring、Dataclass 優先、類別結構順序。
- **新增 §10.4**：Open Claw Workspace 命名規範。
- **新增 §16**：自動化強制工具鏈，指定 Ruff、Mypy、pre-commit，提供 VS Code 標準設定。
- **新增 §18**：禁止模式（Prohibited Patterns），明確列出「不准做什麼」。

### v2.0.0（2026-04-17）—— AI 協作整合版

整合 AI 協作指令集與實作版精華，強化強制約束力：

- **新增 §0**：AI Agent 協作指令集，包含先讀後寫原則、嚴禁假設、無聲修改禁止。
- **更新 §11**：引入功能目錄分層原則（`core/`、`skills/`、`ops/` 定義）。

### v3.0.0（2026-04-18）—— 完整整合版（本版本）

整合所有來源文件（`BASIC_RULES.md`、`CODING_GUIDELINES.md` v1.0 & v2.0、`CODING_GUIDELINES_FINAL.md` v3.1、`CODING_GUIDELINES_實作.md`、`CODING_GUIDELINES_v1_1_0.docx`、對話記錄），形成單一權威文件：

- 保留完整 SOLID 原則說明與程式碼範例
- 整合函數編寫完美主義細則（第 9 章）
- 整合 Open Claw 命名規範（§10.4）
- 整合原子寫入與優雅關閉（§4.6、§4.7）
- 整合自動化工具鏈（第 16 章）
- 整合禁止模式與 Code Review Checklist（第 18 章）
- 整合 Gemini 對話中的分析建議

### v4.0.0（2026-04-30）—— Omega Integration (CLI UI Uniformity)

- **新增 §19**：全鏈路自癒與互動介面操作 (Code Self-Healing and Interactive UI)，確保所有模組 CLI 啟動介面皆遵循單一標竿（如 `audio-transcriber` 的 DAG 面板、互動選取、前置檢查機制）。
- 落實 SSoT 防精簡鐵律，確立 `/docs/` 唯一性，撤銷 Sandbox 目錄下的文檔。

---

## 19. CLI 介面與邏輯標竿 (Omega Integration)

為確保 Open Claw 所有技能模組 (`skills/*`) 具備統一的操作體驗與防錯機制，所有 `run_all.py` 腳本必須嚴格實作以下三層架構：

### 19.1 啟動前置檢查 (Preflight Check)
必須在管線啟動的第一時間執行依賴與環境驗證：
- 必須宣告 `startup_check(self) -> bool`。
- 檢查包含：必要套件是否存在（如 `poppler-utils`、`pydub`）、配置檔是否設定正確（如 `chrome_profile`）、Ollama 伺服器是否可連線。
- 成功需印出 `✈️ 進行啟動前置檢查...` 與 `✅ 前置檢查通過`。

### 19.2 狀態與 DAG 追蹤面板 (Dashboard)
管線啟動後，必須立即呈現當前工作狀態：
- 調用 `self.state_manager.print_dashboard()` 渲染標準的 Markdown/Terminal 表格，顯示各 Phase 的完成比例（如 `✅ 25/25`, `⏳ 22/25`）。

### 19.3 互動式選取與重跑機制 (Interactive Menu)
當無帶入 `--force` 或 `--process-all` 等全量參數時，必須提供互動選單：
- 必須偵測「已完成 (COMPLETED)」檔案與「待處理 (PENDING)」檔案。
- 調用 `core.cli_menu.batch_select_tasks` 呈現清單，允許使用者透過數字與範圍（如 `1,3,5` 或 `1-5`）動態選擇要處理的檔案。
- 若選擇了已完成檔案，必須強制將狀態覆寫為 `PENDING` 進行重跑 (Reprocess)。

---

*本手冊版本：v4.0.0*
*最後更新：2026-04-30*
*維護者：Jinkun & Antigravity*
