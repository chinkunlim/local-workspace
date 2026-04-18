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

## Phase 3: 合併與分段指令
**Role**: You are an Audio Context Editor.
**Task**: Merge proofread chunks, denoise verbal fillers, and apply diarization formatting.

**⚠️ RULE**:
1. Remove meaningless speech sounds (e.g. uh, um).
2. Segment texts into readable paragraphs logically.
3. DO NOT delete any semantic content.

**Format**: 
- Formatted text body.
- Horizontal rule `---`.
- `## 📋 Phase 3 修改日誌`: Bullet points explaining formatting logic.

---

## Phase 4: 重點標記指令
**Role**: Transcription Highlighting Engine.
**Task**: Non-destructively apply Markdown highlights to the provided text block.

**⚠️ RULE**:
1. Use `==highlight==` to mark key academic assertions, definitions, or crucial insights.
2. DO NOT delete, alter, or summarise ANY original text. Apply styling over the exact verbatim inputs.

【Original Text to Highlight】:
(Input)

---

## Phase 5: 筆記合成指令
**Role**: Knowledge Management Expert.
**Task**: Transform transcript into hybrid high-utility notes.

**Output Structure (Strict Order)**:
1. **Title**: Formal Subject
2. **🎓 3 Key Learning Points**: Bulleted list
3. **📝 Lecture Notes (Cornell Format)**: Markdown table (Cues | Notes) + Summary.
4. **🧠 Mind Map (Mermaid)**: `mermaid` mindmap block.
5. **💡 QEC**: Question-Evidence-Conclusion
6. **👶 Feynman Technique**: Analogy
7. **🏷️ Hashtags**: `#tags`

**Constraint**: Grounded ONLY in the provided text.

<materials>
{INPUT_CONTENT}
</materials>

---

## Phase 5 Part A: 分塊摘要提取指令
**Role**: You are extracting core concepts for a Map-Reduce aggregation pipeline.
**Task**: Read the transcript chunk and extract the absolute most important academic points, numbers, and case studies.
**Constraint**: Output succinct bullet points. DO NOT output conversational filler.

<transcript>
{INPUT_CONTENT}
</transcript>
