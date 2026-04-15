# HANDOFF.md — Execution State Tracker

> [!IMPORTANT]
> ## Current State: V7.2 — Dual-Skill Core Alignment & Optimization
> **Objective Achieved**: Extract map-reduce components to `core/text_utils.py`, harmonize `CODING_GUIDELINES.md` with `pdf-knowledge`, and enforce a global `bootstrap.sh` standard. Previous pipeline architectures and top-tier Local Git syncs remain actively sustained.


### Active Architecture

| Phase | Script | Input | Output Dir | Key Mechanism |
| :---: | :--- | :--- | :--- | :--- |
| **0** | `glossary_tool.py` | `01_transcript/` samples | `raw_data/<subject>/glossary.json` | LLM ASR error detection; `--merge` / `--force` / `--glossary-only` modes |
| 1 | `transcribe_tool.py` | `raw_data/` `.m4a` | `01_transcript/` | One line per Whisper segment |
| 2 | `proofread_tool.py` | `01_transcript/` | `02_proofread/` | Glossary + PDF + lookback window + verbatim guard (0.85) + audit log |
| 3 | `merge_tool.py` | `02_proofread/` | `03_merged/` | Glossary + oral filler denoising + lookback (150c) + verbatim guard (0.70) + audit log |
| 4 | `highlight_tool.py` | `03_merged/` | `04_highlighted/` | Strips Phase 3 log before LLM; re-attaches after; anti-tampering (0.95) |
| 5 | `notion_synthesis.py` | `04_highlighted/` | `05_notion_synthesis/` | Strips Phase 3 log + `==markers==` before LLM synthesis |

**Orchestrator**: `run_all.py` (supports `--interactive`, `--from N`, `--force`, `--glossary`, `--glossary-merge`, `--glossary-force`)

### Key Mechanisms Active

1. **Prompt Externalisation**: Every phase reads from `prompt.md` via `sm.get_prompt_from_md()`. No prompts are hard-coded in Python.
2. **Config Externalisation**: Every phase reads from `config.json` via `sm.get_model_config()`. No model names are hard-coded.
3. **Phase 0 — Glossary Auto-Generation**: `glossary_tool.py` reads samples from `01_transcript/`, asks LLM to detect ASR errors, writes draft `glossary.json`. **Must be reviewed by user before Phase 2**. `--merge` mode adds only new entries to existing file (safe for re-runs).
4. **Glossary Injection (Phase 2 & 3)**: `sm.get_glossary(subj)` reads glossary, formats as `【術語詞庫】` block; silent no-op if file absent.
5. **smart_split() Chunking**: All LLM phases now use `sm.smart_split()` — chunks fall on `\n` boundaries, only hard-cuts when single paragraph exceeds chunk_size.
6. **Lookback Context Window**: Phase 2 (200c) and Phase 3 (150c) inject tail of previous chunk as non-output context hint to prevent terminology errors at boundaries.
7. **Verbatim Guard**: Phase 2 (0.85) — fallback to original if output too short. Phase 3 (0.70) — warning if output < 70% of input.
8. **Audit Logs**: Phase 2 appends `## 📋 彙整修改日誌`; Phase 3 appends `## 📋 Phase 3 修改日誌`. Both are deduplicated in Python.
9. **Phase 3 Log Passthrough**: Phase 4 strips Phase 3 log before highlighting, re-attaches to output. Phase 5 also strips it (defensive).
10. **Phase 5 Input Cleaning**: `==highlight==` markers removed before Phase 5 synthesis (no semantic value for note generation).
11. **Empty Response Guard**: `call_ollama()` raises `ValueError` on empty/whitespace response (protects all phases from silent empty-file writes).
12. **Phase 4 Anti-Tampering**: If LLM output < 95% of input, original chunk preserved as fallback.
13. **Checkpoint & Batch UI**: Interactive reprocessing selection, stable sorting, and resumable execution states.
14. **Thread Safety Guarantees**: Background loops (Spinners) explicitly joined using `finally` wrappers, preventing zombie deadlocks during API exceptions.: Interactive reprocessing selection, stable sorting, and resumable execution states.: If LLM output < 95% of input, original chunk preserved as fallback.

### Quick Reference: Recommended LLM Alternatives

| Phase | Current | Recommended |
| :---: | :--- | :--- |
| 0 (Glossary) | `gemma3:12b` | `qwen2.5:14b` (better Chinese domain knowledge) |
| 2 (Proofread) | `gemma3:12b` | `qwen2.5:14b` or `qwen3:14b` |
| 3 (Merge) | `gemma3:12b` | `qwen3:14b` (better oral filler comprehension) |
| 4 (Highlight) | `gemma3:12b` | `qwen3:8b` (same quality, faster) |
| 5 (Notion) | `gemma3:12b` | `qwen3:14b` or `deepseek-r1:14b` |

To switch: change `active_profile` in `config.json` for the target phase.

## Recent Changes (2026-04-09)

| File | Change |
| :--- | :--- |
| `glossary_tool.py` | **NEW** — Phase 0 auto-glossary generator with `--merge`/`--force` modes |
| `prompt.md` | Phase 0 prompt added; version bumped to V5.2 |
| `config.json` | `phase0` profile added (gemma3:12b default, qwen2.5:14b recommended) |
| `run_all.py` | `--glossary`, `--glossary-merge`, `--glossary-force`, `--from 99` flags added |
| `notion_synthesis.py` | Strips `==highlight==` and Phase 3 log before LLM synthesis |
| `subject_manager.py` | `call_ollama()` raises `ValueError` on empty response |
| `proofread_tool.py` | Uses `sm.smart_split()` + chunk_size 3000 |
| `merge_tool.py` | Uses `sm.smart_split()` + lookback 150c + P3 verbatim guard (0.70) |
| `highlight_tool.py` | Strips Phase 3 log before highlighting; re-attaches after |
| `subject_manager.py` | `smart_split()` utility added |
| `config.json` | Qwen2.5:14b + Qwen3:14b alternative profiles for all phases |

## Next Steps for Future Agent

- **Glossary Review**: Run `python3 glossary_tool.py --subject 助人歷程` after Phase 1, review output, then run Phase 2.
- **Filler Exemption**: `「嗯」` in `助人歷程` may be a therapeutic response — consider `_preserve_fillers` in glossary schema.
- **Qwen Evaluation**: Verified! Qwen3:14B now safely runs perfectly under macOS with Unified Memory threshold hotfixes applied. Monitor terminology improvements vs Gemma3.
- **diff_tool.py**: Optional Phase 2.5 HTML diff tool for visual `01_transcript/` vs `02_proofread/` comparison (planned, not implemented).
- **checklist.md char count**: Optional — record `P2:5234c P3:4891c` in note column for length verification.