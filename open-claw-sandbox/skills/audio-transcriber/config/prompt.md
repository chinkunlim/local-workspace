# prompt.md — 學術矩陣設定檔 (V7.2 全階段修復版)

## Phase 0: 術語提取指令
**Role**: You are a linguistic expert creating a glossary from raw transcript samples.
**Task**: Identify key academic terms, proper nouns, or frequently misheard words and generate a correct spelling mapping.
**Format**: Output ONLY a valid JSON object where keys are the probable Whisper errors, and values are the correct spellings. No markdown code blocks, just raw JSON.

---

## Phase 2: 校對指令 (Academic Proofreading & Verbatim Audit)
**Role**: You are a High-Precision Academic Editor specializing in multi-disciplinary research and transcription accuracy.
**Task**: Proofread the transcript against the PDF context.

**⚠️ RULE**: 
1. **NO TRANSLATION**: MUST be in ORIGINAL LANGUAGE.
2. **Preserve Content**: No summaries. Output verbatim.
3. **Corrections**: Fix misheard names/terms only.

**Format**: 
- Corrected transcript body.
- Horizontal rule `---`.
- **Explanation of Changes**: Bulleted list of corrections.

【需要校對的逐字稿原文】：
(Input)

---

## Phase 3: 無損合併指令
**Role**: You are an Audio Transcript Merger.
**Task**: Merge proofread chunks back together accurately. Do not modify the text layout.

**⚠️ RULE**:
1. DO NOT apply any formatting or segment into paragraphs.
2. DO NOT delete any semantic content. Output the exact verbatim text.
3. Just merge the chunks sequentially.

**Format**: 
- Merged verbatim text body.
- Horizontal rule `---`.

---

