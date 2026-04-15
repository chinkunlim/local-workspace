# WALKTHROUGH.md — System Operation Guide (V2.1)

> [!NOTE]
> V2.1 新增：PDF 診斷流程（Phase 1a）、向量圖表處理、OCR 品質警告、術語保護說明。

---

## 🌱 白話解說（完整版）

你只需要把 PDF 丟進一個資料夾，系統會自動：

1. **快速診斷 PDF**（新增）— 5 秒內先檢查：有沒有密碼？字型是否正常？有沒有向量統計圖？
2. **完整提取內容** — 文字、表格、圖片（包含 matplotlib/R 的統計圖）、參考文獻
3. **保護關鍵術語**（新增）— 確保「輔療」不會被 AI 誤寫成「輔料」等相近詞
4. **和 Gemini 討論** — 按學科分配專家，反覆討論直到完全理解
5. **查核並歸檔** — Whitelist 核實 + Voyager 下載整個對話並歸類
6. **呈現可編輯筆記** — 帶思維導圖、來源預覽、版本回溯的離線介面

**你的控制點**：
- 隨時暫停/接管
- 審閱 OCR 品質警告並決定是否人工核對
- 在 Dashboard 標記「綠色療癒潛力」的 PDF
- 在 `whitelist.yaml` 新增信任網站（不需改程式碼）
- 在 `priority_terms.json` 新增需要保護的術語（不需改程式碼）

---

## 🔒 安全設定（首次使用必讀）

**1. 填入 Chrome Profile 路徑**（`config/config.yaml`）:
```yaml
playwright:
  chrome_profile: "/Users/你的名字/Library/Application Support/Google/Chrome/Default"
  account_hint: "工作帳號 / 個人帳號"  # 備忘，啟動時顯示給你確認
```

**2. 確認操作邊界**（`config/security_policy.yaml`）:
系統只被允許前往 `gemini.google.com`，禁止前往 Gmail、Drive、帳號設定頁面。你可以隨時在 Dashboard 的「安全記錄」查看所有操作。

**3. 多帳號確認**:
啟動時終端機顯示：`🔐 Chrome Profile: Default — 備忘: "工作帳號"。這是你想要使用的帳號嗎？[是/否]`
輸入「否」時系統中止，讓你修改 `config.yaml`。

---

## Phase 1a — 輕量診斷（新增，先於 Docling）

### 🌱 白話解說
就像醫生在開刀前先做基本檢查。這 5 秒的診斷能告訴我們 PDF 有沒有加密、字型有沒有問題、哪些頁面有只用 PDF 圖層畫的統計圖（這種圖需要特別處理）。

### 技術細節

```bash
# pdf_diagnostic.py 依序執行：
pdfinfo document.pdf              # 頁數、加密、版本
pdftotext -f 1 -l 1 doc.pdf -    # 首頁採樣（掃描偵測）
pdffonts document.pdf             # 字型健康診斷
pdfimages -list document.pdf      # raster 圖片統計
pdftotext -layout document.pdf -  # 多欄偵測（行寬分析）
```

診斷結果 → `scan_report.json`:
```json
{
  "pages": 48,
  "pdf_type": "digital",
  "is_scanned": false,
  "has_broken_fonts": false,
  "has_raster_images": true,
  "vector_chart_pages": [3, 7, 15],
  "likely_multi_column": true,
  "low_confidence_pages": []
}
```

⚠️ `vector_chart_pages` 非空 → Phase 1c 對這些頁面執行 pdftoppm 光柵化

---

## Phase 1b — Docling 深度提取

同 V2.0，加入字型損壞 fallback：若 `has_broken_fonts: true`，Docling 提取後對問題頁面執行 pdftoppm + OCR 交叉驗證，差異 > 20% 時以 OCR 結果為主。

---

## Phase 1c — 向量圖表補充（新增）

### 🌱 白話解說
心理學論文的統計圖（散佈圖、折線圖、迴歸圖）通常是用軟體（R、SPSS、matplotlib）畫的，存在 PDF 裡是向量格式，用普通方式提取圖片的工具找不到它們。這一步會把那些頁面「拍照存檔」，確保這些重要的統計圖不被遺漏。

### 技術細節
```bash
# 對 scan_report.json 中的 vector_chart_pages 執行：
pdftoppm -jpeg -r 150 -f 3 -l 3 document.pdf /tmp/vec_p3
# 輸出：/tmp/vec_p3-03.jpg → 移動到 assets/fig_p3_vector.jpg
```

圖表在 `figure_list.md` 中標記 `type: "vector_rasterized"`，VLM 描述和數據趨勢標籤的生成方式與 raster 圖片相同。

---

## Phase 1d — OCR 品質評估（新增）

### 🌱 白話解說
掃描 PDF 的文字辨識有時候不準確。這一步會對每個掃描頁面給出一個「信心分數」。信心分數低於 80% 的頁面會被標記——你在最終筆記裡看到橘色警告框就知道哪裡需要手動對照原始頁面。

### 技術細節
```python
# 繁體中文（chi_tra）+ 英文（eng）混合辨識
# 200 DPI（比 150 DPI 準確率高約 15%）
data = pytesseract.image_to_data(img, lang='chi_tra+eng', output_type=Output.DICT)
page_confidence = mean([c/100 for c in data['conf'] if int(c) > 0])

# 若 confidence < 0.80：
# → scan_report.json 記錄 low_confidence_pages
# → Dashboard 黃色警告
# → content.md 段落前插入: > ⚠️ **[OCR品質警告]** 此段信心值 {72%}，建議核對原始頁面
```

---

## Phase 1e — 術語強制保護（新增）

### 🌱 白話解說
AI 有時候會把「輔療」誤寫成「輔料」（聽起來很像但意思完全不同）。這一步在任何 AI 處理文件之前，先做一輪「術語消毒」——強制把所有危險的相近詞換成正確的專業術語。

### 技術細節
```python
# terminology_builder.py 在每次 LLM 呼叫前執行

# Layer 1: 字串替換（進入 LLM 前）
for wrong, correct in priority_terms["CRITICAL_SUBSTITUTIONS"].items():
    text = text.replace(wrong, correct)

# Layer 2: Prompt 注入（控制 LLM 輸出）
prompt_prefix = "【術語保護】以下術語禁止任何形式的同義替換：「輔療」、「動物輔助治療」..."
```

更新 `priority_terms.json`（不需要改程式碼）：
```json
{
  "CRITICAL_SUBSTITUTIONS": {
    "輔料": "輔療",
    "fu liao": "輔療"
  },
  "CRITICAL_TERM_PROTECTION": ["輔療", "動物輔助治療", "綠色療癒"]
}
```

---

## Phase 3 — 代理閉環（V2.1 更新）

### 跨批次術語一致性（新增）

第一個 chunk 的 Agent Loop 完成後：
```python
# global_session_memory.json 建立
{
  "locked_terms": { "Cognitive Load": "認知負荷", ... },
  "locked_at_chunk": { "認知負荷": 1 }
}
```

後續每個 chunk 的 Gemini Prompt 開頭強制包含：
`「【強制術語表】以下術語譯法已鎖定，不得更改：認知負荷=Cognitive Load...」`

### 統計數據保護（新增，當 has_statistics: true）

Agent Loop Prompt 中強制加入：
`「【統計數據保護】禁止修改任何數值（p-value、F-test、效應量、n）。僅可潤飾數值後的文字解釋。」`

### green_care_potential 判斷（新增，最後一輪）

Agent Loop 最後一輪的 Prompt 末尾加入：
`「請評估：這份文件的內容是否有潛力轉化為綠色療癒、農場輔助治療或生態教育的素材？請回答 yes/no 並給出 1-2 句理由。」`

Gemma 讀取回應後更新 `triage.json` 的 `green_care_potential` 欄位。

---

## Phase 5 — 互動輸出（V2.1 新增功能）

### `[G:URL]` 懸浮預覽
滑鼠移到 `[G:URL]` 標籤時 → 呼叫 Flask API `GET /api/source_preview` → 顯示 `source_snapshots/` 中的截圖預覽。Flask 不在線時 → fallback 為純 URL 連結（不顯示截圖）。

### 數據趨勢標籤搜尋
Dashboard 搜尋欄輸入 `Positive_Correlation` → 篩選出所有具有此標籤的圖表，橫跨所有已處理的 PDF。

### green_care_potential 手動標記
Dashboard 每份 PDF 旁有 🌿 按鈕，可覆寫 Gemini 的自動判斷。標記後 `triage.json` 更新，未來「養雞學轉譯器」功能可按此篩選。

---

## Troubleshooting（V2.1 新增）

| 問題 | 原因 | 解決方式 |
| :--- | :--- | :--- |
| 提取結果有亂碼字元 | 字型未嵌入（scan_report: has_broken_fonts: true）| 查看 scan_report.json；對應頁面已啟動光柵化 fallback；若仍有問題，手動對照 PDF 原始頁面 |
| 統計散佈圖沒有被提取到 | 向量圖表被 pdfimages 漏掉 | 確認 scan_report.json 中有 vector_chart_pages；重新觸發 Phase 1c |
| content.md 中出現橘色 OCR 警告 | 掃描品質差（信心值 < 80%）| 開啟 `05_Final_Knowledge/[PDF]/index.html` → 點擊警告段落 → 對照 `02_Processed/[PDF]/assets/` 的原始圖片 |
| chi_tra OCR 語言包缺失 | pytesseract 未安裝繁中語言包 | `brew install tesseract-lang` 或 `sudo apt-get install tesseract-ocr-chi-tra` |
| 術語保護沒有生效 | priority_terms.json 格式錯誤 | 確認 JSON 格式正確；重新觸發 Phase 1e |

---

## 🤖 Antigravity Execution History

### 🕒 [2026-04-13] V2.1
- 新增 Phase 1a/1c/1d/1e 的操作指南（診斷、向量圖、OCR、術語）
- 新增 Phase 3 的跨批次一致性和統計保護說明
- 新增 Phase 5 的懸浮預覽、數據趨勢搜尋、green_care 標記說明
- 新增 4 條 Troubleshooting（字型亂碼、向量圖遺漏、OCR 警告、語言包）
