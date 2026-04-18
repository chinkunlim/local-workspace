# 專業程式開發完整準則手冊
> **版本：** v1.0.0  
> **適用對象：** 所有開發者（Human & AI Agent）  
> **適用工具：** VS Code / Cline、Claude Code、Google Antigravity、任何 IDE  
> **適用規模：** 單人開發 → 小團隊 → 多人協作 → 開源  

---

## 目錄

1. [手冊使用說明](#0-手冊使用說明)
2. [程式碼品質基礎原則](#1-程式碼品質基礎原則)
3. [SOLID 原則](#2-solid-原則)
4. [架構與設計原則](#3-架構與設計原則)
5. [錯誤處理與防禦性程式設計](#4-錯誤處理與防禦性程式設計)
6. [可維護性原則](#5-可維護性原則)
7. [測試原則](#6-測試原則)
8. [安全與效能原則](#7-安全與效能原則)
9. [程式碼風格與格式](#8-程式碼風格與格式)
10. [命名規範](#9-命名規範)
11. [專案結構標準](#10-專案結構標準)
12. [手冊文件體系（Human + AI 雙軌）](#11-手冊文件體系human--ai-雙軌)
13. [Git 版本控制規範](#12-git-版本控制規範)
14. [環境變數與設定管理](#13-環境變數與設定管理)
15. [API 設計規範](#14-api-設計規範)
16. [各階段啟用原則](#15-各階段啟用原則)
17. [快速參考總表](#16-快速參考總表)
18. [版本演進與背景記錄](#17-版本演進與背景記錄)

---

## 0. 手冊使用說明

### 適用對象

本手冊同時適用於：

- **人類開發者**：作為日常開發的行為準則
- **AI Agent**（Cline、Claude Code、Google Antigravity 等）：作為進入任何專案時的第一份讀物

### AI Agent 使用指引

> 所有 AI Agent 在執行任何任務前，**必須先閱讀此手冊**，以及專案 `memory/` 目錄下的所有 `.md` 文件。

```
進入專案流程：
1. 閱讀 CODING_GUIDELINES.md（本文件）
2. 閱讀 memory/CLAUDE.md（專案規則）
3. 閱讀 memory/ARCHITECTURE.md（系統架構）
4. 閱讀 memory/HANDOFF.md（上次進度）
5. 閱讀 memory/TASKS.md（當前任務）
6. 開始執行任務
```

### 原則優先順序

當原則之間發生衝突時，依照以下順序決定優先級：

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
    def __init__(self, api_key: str):
        self._api_key = api_key  # 私有，外部不能直接存取
        self._cache = {}         # 私有實作細節

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
    # 驗證
    if not user.email:
        raise ValueError("Email required")
    # 格式化
    user.name = user.name.strip().title()
    # 儲存
    db.save(user)
    # 發送通知
    send_welcome_email(user.email)

# ✅ 正確示範 — 職責分離
def validate_user(user) -> None:
    if not user.email:
        raise ValueError("Email required")

def format_user(user) -> User:
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

# ❌ 不好的布林命名
active = True

# ✅ 好的布林命名
is_user_active = True
has_permission = False
can_edit = True
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
    if format_type == "csv":
        ...
    elif format_type == "json":
        ...
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
    def __init__(self, db: Database):  # 依賴抽象
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

| 層級     | 說明                         | 問題                 |
| -------- | ---------------------------- | -------------------- |
| 無抽象   | 直接寫二進位 / 低階操作      | 難以閱讀和維護       |
| 適度抽象 | 抽出核心邏輯、公開類別和方法 | ✅ 理想狀態           |
| 過度抽象 | 為了抽象而抽象，層層包裝     | 難以追蹤，過度工程化 |

---

### 3.7 減少全域依賴（Reduce Global Dependencies）

**定義：** 避免使用全域變數和全域狀態。

```python
# ❌ 全域狀態
current_user = None  # 全域變數，難以追蹤和測試

def get_user_name():
    return current_user.name

# ✅ 透過參數傳遞
def get_user_name(user: User) -> str:
    return user.name
```

---

### 3.8 Design Patterns（設計模式）

適時使用設計模式，但不強求。三大類別：

| 類別                     | 常用模式           | 適用場景           |
| ------------------------ | ------------------ | ------------------ |
| **Creational（建立型）** | Factory, Singleton | 控制物件的建立方式 |
| **Structural（結構型）** | Adapter, Proxy     | 組合物件和類別     |
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
        raise KeyError(f"Config key '{key}' not found. Available keys: {list(config.keys())}")
    return config[key]
```

---

### 4.2 防禦性程式設計

**定義：** 永遠不信任外部輸入。

**外部輸入包括：**
- API 請求參數
- 使用者輸入
- 資料庫讀取結果
- 第三方 API 回應
- 環境變數

```python
def create_user(data: dict) -> User:
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

### 4.5 Robustness（健壯性）

系統應能應對以下威脅而不崩潰：

| 威脅類型                       | 應對策略                     |
| ------------------------------ | ---------------------------- |
| Input Error（錯誤輸入）        | 輸入驗證 + 清晰錯誤訊息      |
| Network Overload（網路過載）   | Retry 機制 + Circuit Breaker |
| Disk Failure（磁碟故障）       | 定期備份 + 異常捕捉          |
| Intentional Attack（惡意攻擊） | 見安全原則章節               |

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
- **限制巢狀層數：** 超過 3 層立即重構
- **參數不超過 3 個：** 超過 3 個改用物件傳入
- **避免 GOTO：** 製造不可追蹤的控制流

```python
# ❌ 參數過多
def create_event(title, date, time, location, description, is_public, max_attendees):
    ...

# ✅ 用物件包裝
@dataclass
class EventData:
    title: str
    date: date
    time: time
    location: str
    description: str = ""
    is_public: bool = True
    max_attendees: int = 100

def create_event(event: EventData) -> Event:
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

| 類型             | 目的             | 速度 | 位置                 |
| ---------------- | ---------------- | ---- | -------------------- |
| Unit Test        | 測試單一函數邏輯 | 快   | `packages/*/tests/`  |
| Integration Test | 測試模組間互動   | 中   | `tests/integration/` |
| E2E Test         | 測試完整使用流程 | 慢   | `tests/e2e/`         |

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

> **符合現有 codebase 的風格，即使你個人不喜歡。**
> 一致性比個人偏好更重要。

---

### 8.2 格式規範

| 項目     | 規範                                                 |
| -------- | ---------------------------------------------------- |
| 縮排     | 2 或 4 個空格，全專案統一（Python 用 4，JS/TS 用 2） |
| 行寬     | 最大 100 字元（Python：88，JS/TS：100）              |
| 空白行   | 邏輯區塊之間用空行隔開                               |
| 括號風格 | 全專案統一一種風格                                   |
| 行尾     | 統一使用 LF（Unix 換行）                             |
| 檔案結尾 | 最後一行保留空白行                                   |

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

| 語言       | 規範工具              | 設定檔                           |
| ---------- | --------------------- | -------------------------------- |
| Python     | Black + Flake8 + mypy | `pyproject.toml`                 |
| TypeScript | ESLint + Prettier     | `.eslintrc.json` + `.prettierrc` |
| JavaScript | ESLint + Prettier     | 同上                             |

---

## 9. 命名規範

### 9.1 命名風格

| 風格               | 格式            | 適用場景                       |
| ------------------ | --------------- | ------------------------------ |
| `camelCase`        | `variableName`  | JS/TS 變數和函數               |
| `PascalCase`       | `ClassName`     | 類別（各語言通用）、React 元件 |
| `snake_case`       | `variable_name` | Python 變數和函數              |
| `UPPER_SNAKE_CASE` | `CONSTANT_NAME` | 常數                           |
| `kebab-case`       | `file-name`     | 檔案名稱、URL                  |

---

### 9.2 命名規則

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

### 9.3 檔案命名規範

| 類型       | 規範                          | 範例                                  |
| ---------- | ----------------------------- | ------------------------------------- |
| 一般程式檔 | `kebab-case`                  | `weather-service.py`                  |
| 類別檔案   | `PascalCase` 或 `kebab-case`  | `WeatherService.py`                   |
| 測試檔案   | `test_` 前綴 或 `.test.`      | `test_weather.py` / `weather.test.ts` |
| 設定檔     | 小寫或 `.` 開頭               | `config.yaml` / `.env`                |
| 手冊文件   | 全大寫                        | `README.md` / `CLAUDE.md`             |
| 型別定義   | `types.` 或 `.d.ts`           | `types.py` / `api.d.ts`               |
| 常數檔案   | `UPPER_SNAKE` 或 `constants.` | `constants.py`                        |

---

## 10. 專案結構標準

### 10.1 Monorepo 完整結構

```
my-project/
│
├── .github/                        # GitHub 相關設定
│   ├── workflows/                  # CI/CD（GitHub Actions）
│   │   ├── test.yml                # 自動測試
│   │   ├── lint.yml                # 程式碼品質檢查
│   │   └── deploy.yml              # 部署流程
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   └── PULL_REQUEST_TEMPLATE.md
│
├── apps/                           # 各子系統（可獨立運行）
│   ├── api/                        # 對外 REST/GraphQL API
│   │   ├── src/
│   │   │   ├── routes/             # 路由定義
│   │   │   ├── controllers/        # 請求處理
│   │   │   ├── middleware/         # 認證、限流等
│   │   │   └── main.py
│   │   ├── tests/
│   │   └── README.md
│   ├── telegram-bot/               # Telegram 接入層
│   │   ├── src/
│   │   ├── tests/
│   │   └── README.md
│   ├── web/                        # Web 前端（若有）
│   │   ├── src/
│   │   ├── public/
│   │   └── README.md
│   └── worker/                     # 背景排程 / 自動化任務
│       ├── src/
│       └── README.md
│
├── packages/                       # 跨子系統共用模組
│   ├── core/                       # 核心業務邏輯
│   ├── db/                         # 資料庫 schema + 存取層
│   ├── types/                      # 共用型別定義
│   └── utils/                      # 通用工具函數
│
├── infra/                          # 基礎設施設定
│   ├── docker/
│   │   ├── Dockerfile
│   │   └── docker-compose.yml
│   ├── nginx/
│   │   └── nginx.conf
│   └── scripts/                    # 部署 / 初始化腳本
│       ├── setup.sh
│       └── migrate.sh
│
├── docs/                           # 對外文件（開源用）
│   ├── api/                        # API 文件
│   │   ├── openapi.yaml            # OpenAPI 規格
│   │   ├── VERSIONING.md           # 版本策略
│   │   ├── RATE_LIMITING.md        # 限流規則
│   │   └── AUTH.md                 # 認證說明
│   ├── architecture/               # 系統架構圖
│   │   ├── overview.md
│   │   └── diagrams/
│   └── guides/                     # 使用教學
│       ├── quickstart.md
│       └── deployment.md
│
├── memory/                         # AI 協作記憶體系統
│   ├── CLAUDE.md                   # AI 專案總覽與行為規則
│   ├── HANDOFF.md                  # 跨 session 交接狀態
│   ├── TASKS.md                    # 當前任務清單
│   ├── DECISIONS.md                # 重要決策記錄
│   ├── ARCHITECTURE.md             # 系統架構說明
│   └── agents/                     # 各 AI Agent 專屬設定
│       ├── cline.md
│       ├── claude-code.md
│       └── google-antigravity.md
│
├── tests/                          # 全域測試
│   ├── e2e/                        # End-to-end 測試
│   └── integration/                # 跨模組整合測試
│
├── .env.example                    # 環境變數範本（提交到 git）
├── .gitignore
├── .editorconfig                   # 跨編輯器風格統一
├── README.md                       # 專案入口
├── CHANGELOG.md                    # 版本變更記錄
├── CONTRIBUTING.md                 # 貢獻指南（開源準備）
├── SECURITY.md                     # 安全漏洞回報流程
├── LICENSE                         # 授權聲明
└── pyproject.toml / package.json   # 依語言而定
```

---

### 10.2 子模組內部結構規範

每個 `apps/*` 和 `packages/*` 內部應遵循：

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
├── README.md                      # 此模組的說明
└── requirements.txt 或 package.json
```

---

## 11. 手冊文件體系（Human + AI 雙軌）

### 11.1 文件分層架構

```
文件體系
├── AI 讀取層（memory/）          # AI Agent 優先讀取
├── Human 協作層（根目錄）         # 團隊成員讀取
└── API 文件層（docs/api/）        # 外部使用者讀取
```

---

### 11.2 AI 讀取層（`memory/`）

> 所有 AI Agent 進入專案時**必須按順序閱讀**此目錄下的文件。

| 檔案              | 用途                                 | 更新時機            | 負責人     |
| ----------------- | ------------------------------------ | ------------------- | ---------- |
| `CLAUDE.md`       | 專案規則、AI 行為準則、禁止事項      | 規則改變時          | 專案負責人 |
| `HANDOFF.md`      | 上次做到哪、下次從哪開始、未解決問題 | 每次 session 結束時 | 最後工作者 |
| `TASKS.md`        | 待辦、進行中、已完成任務             | 每次任務狀態變動    | 當前工作者 |
| `DECISIONS.md`    | 為什麼選這個技術或架構的決策記錄     | 重大決策後          | 決策者     |
| `ARCHITECTURE.md` | 系統全貌、資料流、模組關係圖         | 架構變動時          | 架構負責人 |

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

### 11.3 Human 協作層（根目錄）

| 檔案                 | 用途                         | 必要性         |
| -------------------- | ---------------------------- | -------------- |
| `README.md`          | 專案介紹、快速啟動、徽章     | ✅ 必要         |
| `CONTRIBUTING.md`    | 如何貢獻程式碼、PR 流程      | 小團隊起開始   |
| `CHANGELOG.md`       | 每個版本做了什麼（語意版本） | ✅ 必要         |
| `LICENSE`            | 授權聲明                     | 開源前必要     |
| `SECURITY.md`        | 如何回報安全漏洞             | 多人協作起開始 |
| `CODE_OF_CONDUCT.md` | 社群行為準則                 | 開源前必要     |

#### `README.md` 必要內容

```markdown
# 專案名稱

> 一句話描述

[![Tests](badge-url)](link)
[![License](badge-url)](link)

## 快速開始
（3步驟以內能讓人跑起來）

## 功能特色
## 系統需求
## 安裝說明
## 使用範例
## API 文件連結
## 貢獻方式
## 授權
```

---

### 11.4 API 文件層（`docs/api/`）

| 檔案               | 用途                             |
| ------------------ | -------------------------------- |
| `openapi.yaml`     | OpenAPI 3.0 規格定義（機器可讀） |
| `VERSIONING.md`    | 版本策略（v1/v2 升版規則）       |
| `RATE_LIMITING.md` | 限流規則、配額說明               |
| `AUTH.md`          | 認證方式、Token 申請流程         |

---

## 12. Git 版本控制規範

### 12.1 Branch 命名

```
main              # 穩定版，永遠可部署，受保護
develop           # 開發主線，整合測試後合併到 main
feature/xxx       # 新功能（e.g., feature/telegram-weather-alert）
fix/xxx           # 修 bug（e.g., fix/api-null-response）
docs/xxx          # 純文件更新（e.g., docs/update-api-guide）
refactor/xxx      # 重構，不改功能（e.g., refactor/extract-weather-service）
test/xxx          # 補測試
chore/xxx         # 工具、設定、依賴更新
release/vX.Y.Z    # 發版準備（e.g., release/v1.2.0）
hotfix/xxx        # 緊急修復生產環境 bug
```

---

### 12.2 Commit 訊息規範（Conventional Commits）

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

### 12.3 PR（Pull Request）規範

- PR 只做一件事
- PR 描述說明「為什麼」這樣改
- 合併前必須通過 CI 測試
- 至少一位 reviewer 批准（小團隊起）
- 使用 Squash Merge 保持 main branch 歷史清晰

---

### 12.4 `.gitignore` 必要項目

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

## 13. 環境變數與設定管理

### 13.1 三層環境設定

```
環境層級：
├── .env.example     # ✅ 提交到 git（範本，無真實值）
├── .env.local       # ❌ 不提交（本機開發用）
├── .env.test        # ❌ 不提交（測試環境）
└── .env.production  # ❌ 不提交（走 CI/CD secrets）
```

---

### 13.2 `.env.example` 標準格式

```bash
# ================================
# 應用程式設定
# ================================
APP_NAME=my-project
APP_ENV=development          # development | staging | production
APP_PORT=3000
APP_SECRET_KEY=              # 必填：openssl rand -hex 32

# ================================
# API 版本
# ================================
API_VERSION=v1

# ================================
# 資料庫
# ================================
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
# 或 SQLite 開發用：
# DATABASE_URL=sqlite:///./dev.db

# ================================
# Telegram Bot
# ================================
TELEGRAM_BOT_TOKEN=          # 必填：從 @BotFather 取得

# ================================
# 外部 API
# ================================
CWA_API_KEY=                 # 中央氣象署 API Key
GEMINI_API_KEY=              # Google Gemini API Key

# ================================
# 快取（可選）
# ================================
REDIS_URL=redis://localhost:6379/0
```

---

### 13.3 讀取環境變數規範

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
API_VERSION = os.environ.get("API_VERSION", "v1")

# ✅ 必填變數
DATABASE_URL = get_required_env("DATABASE_URL")
TELEGRAM_BOT_TOKEN = get_required_env("TELEGRAM_BOT_TOKEN")
```

---

## 14. API 設計規範

### 14.1 版本控制

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

### 14.2 REST API 命名規範

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

### 14.3 回應格式標準

```json
{
  "success": true,
  "data": { ... },
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

### 14.4 HTTP 狀態碼規範

| 狀態碼 | 用途                       |
| ------ | -------------------------- |
| 200    | 成功                       |
| 201    | 建立成功                   |
| 204    | 成功但無回應內容（刪除）   |
| 400    | 請求格式錯誤               |
| 401    | 未認證                     |
| 403    | 無權限                     |
| 404    | 資源不存在                 |
| 422    | 驗證失敗                   |
| 429    | 請求過於頻繁（Rate Limit） |
| 500    | 伺服器內部錯誤             |

---

## 15. 各階段啟用原則

隨著專案成長，逐步啟用更多規範。不要在單人階段就引入所有開銷。

### 階段一：單人開發

**啟用：**
- `memory/` 目錄完整建立
- `README.md` + `.env.example`
- Git branch 規範（main + feature branches）
- Conventional Commits
- `.editorconfig` + `.gitignore`
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

## 16. 快速參考總表

### 原則速查

| 類別       | 原則             | 一句話說明                 |
| ---------- | ---------------- | -------------------------- |
| 程式碼品質 | DRY              | 不重複                     |
| 程式碼品質 | 封裝             | 隱藏細節，暴露介面         |
| 程式碼品質 | SRP              | 一個函數只做一件事         |
| 程式碼品質 | 命名即文件       | 看名字就知道做什麼         |
| SOLID      | S                | 單一職責                   |
| SOLID      | O                | 擴展開放，修改封閉         |
| SOLID      | L                | 子類別可替換父類別         |
| SOLID      | I                | 介面要小而專               |
| SOLID      | D                | 依賴抽象，不依賴具體       |
| 架構       | KISS             | 保持簡單                   |
| 架構       | YAGNI            | 不預先寫不需要的功能       |
| 架構       | 關注點分離       | UI / 邏輯 / 資料各自獨立   |
| 架構       | 模組化           | 可拆開、可替換、可獨立測試 |
| 架構       | 最小知識         | 只跟直接相關的互動         |
| 架構       | 適度抽象         | 不過度也不不足             |
| 架構       | 減少全域依賴     | 用參數傳遞，不用全域變數   |
| 錯誤       | Fail Fast        | 錯了就立刻停               |
| 錯誤       | 防禦性           | 永遠驗證外部輸入           |
| 錯誤       | Robustness       | 面對威脅不崩潰             |
| 維護       | 可讀性 > 聰明    | 寫給人看，不是寫給機器看   |
| 維護       | 持續重構         | 邊走邊清，不等爛掉         |
| 維護       | 文件說 Why       | 程式碼說 What，文件說 Why  |
| 測試       | 可測試性         | 設計時就考慮測試           |
| 測試       | 覆蓋關鍵路徑     | 不追求 100%，保護核心邏輯  |
| 安全       | 最小權限         | 只申請必要權限             |
| 安全       | 不硬寫密鑰       | 走環境變數                 |
| 安全       | 防 SQL Injection | 用參數化查詢               |
| 效能       | 不過早優化       | 先正確，再優化             |
| 效能       | 量測後再優化     | 用數據決定優化點           |

---

### 文件速查

| 文件                     | 主要讀者                | 更新頻率     |
| ------------------------ | ----------------------- | ------------ |
| `memory/CLAUDE.md`       | AI Agent                | 規則改變時   |
| `memory/HANDOFF.md`      | AI Agent + 下一位工作者 | 每次 session |
| `memory/TASKS.md`        | AI Agent + 當前工作者   | 每日         |
| `memory/DECISIONS.md`    | AI Agent + 全團隊       | 重大決策後   |
| `memory/ARCHITECTURE.md` | AI Agent + 全團隊       | 架構變動時   |
| `README.md`              | 新成員 + 外部使用者     | 功能更新時   |
| `CONTRIBUTING.md`        | 貢獻者                  | 流程改變時   |
| `CHANGELOG.md`           | 使用者 + 團隊           | 每次發版     |
| `docs/api/openapi.yaml`  | API 使用者 + AI Agent   | API 變動時   |

---

## 17. 版本演進與背景記錄 (Evolution & Context)

本章節紀錄了本準則手冊的決策過程與功能演進，確保開發原則具有追溯性。

### 1. 核心開發與品質原則 (Core Development & Quality)
* **2026-04-17 08:40 AM**：初步討論專業設計基礎，確立封裝、DRY 與操作規範為核心。
* **2026-04-17 08:47 AM**：定義 **DRY (Don't Repeat Yourself)**、**封裝 (Encapsulation)**、**單一職責 (SRP)** 與「命名即文件」作為品質基礎。
* **2026-04-17 09:06 AM**：在準則中落實具體實踐方法，定義重複邏輯抽離規範並提供實作範例。

### 2. 架構設計與 SOLID 規範 (Architecture & SOLID)
* **2026-04-17 08:47 AM**：確立 **SOLID** 五大原則為物件導向核心，並引入 **KISS**、**YAGNI** 與 **最小知識原則**。
* **2026-04-17 09:06 AM**：細化「適度抽象」與「減少全域依賴」的架構建議，落實關注點分離 (SoC)。

### 3. 錯誤處理與安全性 (Error Handling & Security)
* **2026-04-17 08:47 AM**：提出 **Fail Fast**（快速失敗）、防禦性程式設計及環境變數管理密鑰規範。
* **2026-04-17 09:06 AM**：整合 SQL 注入與 XSS 防護規範，定義錯誤訊息應包含 What, Where, How 三要素。

### 4. 工程規範與自動化管理 (Engineering Standards & Workflow)
* **2026-04-17 08:47 AM**：規範 Git 提交習慣、單元測試覆蓋核心路徑，以及註解應說明「為什麼」而非「做什麼」。
* **2026-04-17 09:06 AM**：整合 `.editorconfig` 配置以統一格式，並確立 **Human + AI 雙軌文件體系**與專案結構標準化（如 `src/`, `tests/`）。
 
---

*本手冊版本：v1.0.0*  
*最後更新：依照實際日期填寫*  
*維護者：依照實際人員填寫*

---

## 18. Open Claw Workspace 命名規範（Naming Convention）

> **狀態：正式規範 v1.0 — 2026-04-17 制定**
> 此章節為 Open Claw Workspace 的 **唯一命名法則來源**。所有 Human Developer 和 AI Agent 必須遵守，違反則視為 Lint Error。

### 18.1 核心原則

命名規範的最高指導原則：**一致性優於個人偏好**。全專案統一一種風格，比「個別情況下的最佳風格」更重要。

### 18.2 完整命名對照表

| 適用範疇 | 命名法則 | 格式 | 範例 |
|:---|:---|:---|:---|
| **資料目錄** (`data/<skill>/`) | `lower_snake_case` | `01_processed` | `input`, `01_processed`, `02_highlighted`, `error` |
| **Skill 目錄** (`skills/`) | `kebab-case` | `my-skill` | `pdf-knowledge`, `voice-memo` |
| **Core 模組檔案** (`core/`) | `snake_case` | `module_name.py` | `pipeline_base.py`, `log_manager.py`, `session_state.py` |
| **Phase 腳本檔案** | `snake_case` + 相位前綴 | `pNNx_description.py` | `p01a_engine.py`, `p02_highlight.py` |
| **Python 類別** | `PascalCase` | `ClassName` | `Phase1aPDFEngine`, `ResumeManager`, `SessionState` |
| **Python 函數 / 方法** | `snake_case` | `function_name()` | `run()`, `save_checkpoint()`, `_should_keep_image()` |
| **Python 常數** | `UPPER_SNAKE_CASE` | `CONSTANT_NAME` | `MIN_RETENTION_RATIO`, `DEBOUNCE_SECONDS` |
| **Config / YAML 鍵值** | `snake_case` | `key_name` | `timeout_seconds`, `chunk_size`, `min_area_px` |
| **系統文件 / 規範文件** | `UPPER_SNAKE_CASE` | `DOCUMENT_NAME.md` | `CODING_GUIDELINES.md`, `SKILL.md`, `BASIC_RULES.md` |
| **環境變數** | `UPPER_SNAKE_CASE` | `ENV_VAR_NAME` | `WORKSPACE_DIR`, `HF_HOME` |
| **Git 分支** | `kebab-case` | `feature/fix/refactor-name` | `feature/session-state`, `fix/log-verbosity` |

### 18.3 特殊前綴規則

- **相位腳本**：使用 `p` + 兩位數相位編號 + 可選子碼字母，例如 `p00a`, `p01b`, `p03`。
- **私有方法 / 屬性**：前綴 `_`，例如 `_should_keep_image()`, `_write_session_state()`.
- **隱藏狀態檔**：前綴 `.`，例如 `.pipeline_state.json`, `.DS_Store`（macOS 自動產生，不納入版控）.

### 18.4 ❌ 反模式（禁止使用）

```
❌ data/01_Inbox     → ✅ data/input
❌ data/02_Processed → ✅ data/output/01_processed
❌ data/03_AgentCore → ✅ data/state/resume
❌ data/Error        → ✅ data/output/error
❌ MyModule.py       → ✅ my_module.py  (Core/Phase 腳本皆用 snake_case)
❌ SKILL-NAME/       → ✅ skill-name/   (Skill 目錄用 kebab-case 全小寫)
❌ timeoutSeconds    → ✅ timeout_seconds (YAML 鍵值用 snake_case)
```

### 18.5 命名一致性驗證流程

每次 AI Agent 或開發者新增或重新命名任何檔案、目錄、變數時，必須執行此心智核查：

1. **類型識別**：這是什麼？（目錄？Python 類別？常數？文件？）
2. **查表對照**：對照 18.2 表格找到對應的命名法則。
3. **套用法則**：嚴格按照法則命名，不依照「感覺」或「類比其他語言」。
4. **掃描衝突**：確認全工作區不存在同名但大小寫不同的項目（特別注意 macOS APFS 不區分大小寫的特性）。

