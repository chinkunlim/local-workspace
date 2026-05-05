# [Archived] Phase 2 & 3 Optimization Plan — Glossary Injection & Transcript Refinement

> **Date:** Unknown
> **Session ID:** `565531e0`

---

## 1. Implementation Plan

# Phase 2 & 3 Optimization Plan — Glossary Injection & Transcript Refinement

## Background

The current V5.0 pipeline (5 phases) is stable. This plan evaluates and proposes two optimization layers:
- **Phase 2 (proofread_tool.py)**: Inject a per-subject `glossary.json` as LLM context so the model can correctly normalise domain jargon (e.g., typos in counselling terminology produced by Whisper).
- **Phase 3 (merge_tool.py)**: Add a "術語與數據校準" (Terminology & Data Calibration) instruction block addressing three systematic transcript defects: oral noise denoising, data precision enforcement, and pronoun resolution.

---

## Feasibility Assessment

### ✅ Phase 2 — `glossary.json` Injection

**Verdict: Highly feasible and strongly recommended.**

| Axis | Evaluation |
|:---|:---|
| **Implementation difficulty** | Low — just read one JSON file and format it into the `full_prompt` string. |
| **Quality improvement** | High — Whisper consistently mishears academic jargon (e.g., "輔療雞" vs "輔療」技"，"折中" vs "折衷"). A reference table eliminates these at the correction stage where we still have the PDF. |
| **Robustness** | Graceful degradation: if `glossary.json` doesn't exist for a subject, Phase 2 silently continues without it (no breaking change). |
| **Maintainability** | Excellent — curated by the user per subject, stored next to the audio files in `raw_data/<subject>/glossary.json`, managed by `subject_manager.py`. |

**Proposed glossary.json location**: `raw_data/<subject>/glossary.json`
This mirrors the PDF co-location convention already established for Phase 2.

**Proposed glossary.json format**:
```json
{
  "輔料": "輔療技",
  "折中": "折衷",
  "EST": "Empirically Supported Treatments",
  "理整": "理論整合"
}
```
Format: `"Whisper misrecognition" → "correct academic term"`.

---

### ✅ Phase 3 — Transcript Refinement Rules

**Verdict: Feasible. Effectiveness varies by rule — see nuanced analysis below.**

#### Rule A — 消除冗餘語 (Denoising Oral Fillers)

**Verdict: ✅ Recommended, with caveats.**

- Removing pure noise tokens (「呃」、「那個」、「就是說」) is safe and improves readability.
- **Caveat**: Phase 2's `prompt.md` currently has `Preserve Fillers` as a CRITICAL RULE (Rule #3). This rule exists to protect **verbatim fidelity** in the proofreading stage. Denoising should happen at Phase 3, not Phase 2, because Phase 3 is about **restructuring into a readable document**, unlike Phase 2 which is a 1:1 corrector.
- The existing Phase 3 prompt already says "DO NOT summarize" and "100% text retention" — we need to carve out an explicit exception for **defined filler tokens** to avoid LLM confusion.
- **Recommendation**: Add an explicit ordered filler list to Phase 3 prompt so the LLM removes *only listed tokens* rather than making autonomous summarization judgments.

#### Rule B — 數據精確性 (Data Integrity: Audio vs. PDF)

**Verdict: ✅ Recommended, but enforcement belongs in Phase 2 not Phase 3.**

- Phase 3 (`merge_tool.py`) does **not** receive the PDF as context — it only reads `02_proofread/` files.
- Phase 2 (`proofread_tool.py`) already has PDF access. Adding the data integrity rule there is the architecturally correct placement.
- **Recommendation**: Add this as an explicit rule to the Phase 2 prompt: *"If the transcript says 'approximately 80%' but the PDF explicitly states 86%, write 86%."*
- For Phase 3, if we want to double-enforce, we would need to pass the PDF path forward — which adds complexity. Better handled as a Phase 2 responsibility.

#### Rule C — 補完主語 (Subject Recovery / Pronoun Resolution)

**Verdict: ✅ Recommended for Phase 3.**

- Phase 3 has the full context of the merged lecture, making it the ideal place for pronoun resolution after the document is coherent.
- Instructions must be precise: list which pronouns to resolve (`它`、`這個理論`、`這種方法`) and how (replace with the nearest explicit antecedent noun mentioned in the current paragraph).
- **Caveat**: Without retrieval-augmented grounding, the LLM may hallucinate incorrect antecedents. Instruction should specify: *"Only replace if the concrete antecedent appears explicitly within the same or immediately preceding paragraph."*

---

## Additional Improvements Identified

Beyond the user's proposals, two more optimizations are recommended:

### 🆕 Improvement D — Phase 2 Chunk Overlap (Sliding Window)

**Problem**: The current chunking in `proofread_tool.py` uses hard cuts every 2000 chars. If a term spans a chunk boundary, both chunks lose context.

**Solution**: Use a sliding window with ~200 char overlap between chunks to prevent boundary-context loss. This is a pure code change in `proofread_tool.py`.

### 🆕 Improvement E — `glossary.json` as Phase 3 Context (Lightweight)

If Phase 3 receives the glossary, it can also normalize any terms that slipped past Phase 2. Because it doesn't have PDF access, the glossary becomes its sole domain reference. This is worth adding since glossary injection is cheap (JSON is tiny).

---

## Proposed Changes

### `raw_data/<subject>/glossary.json` [NEW per subject]
- File managed by the user, stored alongside audio and PDFs.
- Format: flat key-value JSON map of `{misrecognition: correct_term}`.

---

### `subject_manager.py` [MODIFY]
#### [MODIFY] [subject_manager.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/subject_manager.py)
- Add `get_glossary(subject)` utility function that reads `raw_data/<subject>/glossary.json`.
- Returns a formatted string block for injection into prompts (e.g., `"輔料" → "輔療技"`).
- Gracefully returns empty string if file is absent.

---

### `proofread_tool.py` [MODIFY]
#### [MODIFY] [proofread_tool.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/proofread_tool.py)
- Call `sm.get_glossary(subj)` before the chunk loop.
- Inject glossary block into `full_prompt` between PDF context and transcript chunk.
- Add Data Integrity rule to the **code-injected context** (not prompt.md, because the rule is data-specific and varies by file).
- *(Optional)* Add sliding-window chunking overlap of ~200 chars.

---

### `merge_tool.py` [MODIFY]
#### [MODIFY] [merge_tool.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/merge_tool.py)
- Call `sm.get_glossary(subj)` before chunk processing.
- Inject glossary as a lightweight term reference in Phase 3 prompt.

---

### `prompt.md` [MODIFY]
#### [MODIFY] [prompt.md](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/prompt.md)
- **Phase 2**: Add Rule #6 for **Data Integrity** — "When the transcript says 'approximately X%' but the PDF explicitly states Y%, use Y%."
- **Phase 3**: Replace the generic "100% text retention" with a refined rule set:
  - Oral filler removal (explicit token list).
  - Subject/pronoun resolution rule (with conservative constraint).
  - Add new section: `術語與數據校準`.

---

## Open Questions

> [!IMPORTANT]
> **1. Glossary file format**: The example `{"輔料": "輔療雞"}` seems like a typo in the example itself — did you mean `"輔療技"` (counselling technique)?  
> Please confirm the intended correct term before we populate the example glossary.

> [!IMPORTANT]
> **2. Phase 3 PDF access**: Should Phase 3 (merge_tool) also receive the PDF for Data Integrity enforcement, or is Phase 2 the sole responsible party?  
> Current recommendation: Phase 2 only. Changing this would require architectural changes to merge_tool.

> [!NOTE]
> **3. Filler removal scope**: Are there subject-specific fillers (e.g., in `助人歷程`, certain fillers like "嗯" might be therapeutic responses and should be preserved)?  
> If yes, the filler token list should be part of `glossary.json` or a separate `config.json` field.

---

## Verification Plan

### Automated
- Run Phase 2 on an existing transcript with a known misrecognition; verify the glossary term appears in the output.
- Run Phase 3 on a merged file with known filler tokens; confirm they are removed in output.

### Manual
- Side-by-side diff of `02_proofread/<subject>/L01.md` before and after glossary injection.
- Review Phase 3 output for pronoun resolution correctness (human audit required).


---

## 2. Walkthrough / Summary

*(No Walkthrough)*

---

## 3. Tasks Executed

*(No Task List)*
