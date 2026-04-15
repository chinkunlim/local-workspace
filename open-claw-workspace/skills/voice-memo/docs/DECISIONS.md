# DECISIONS.md — Design Rationale

> [!NOTE]
> Architecture Decision Record (ADR). 此文件記述了為何捨棄特定方案（如 Docker、Llama），以及為何堅持特定架構（如 Map-Reduce、Qwen）。未來 AI 不得在未審視此處的歷史血淚前，隨意建議推翻基礎決策。

## 1. Local-First Processing
> [!IMPORTANT]
> - **Decision**: Use local Faster-Whisper, MLX-Whisper and Ollama instances.
> - **Rationale**: Ensures academic data privacy and eliminates API costs for long-form lectures.

## 2. Governed Resource Defense
- **Decision**: Implementation of `check_system_health` in the core manager.
- **Rationale**: Since the MacBook Pro M5 has limited shared memory (16GB), heavy inference must be throttled to prevent system freezing or thermal degradation.

## 3. SHA-256 Content Auditing
- **Decision**: Use hash-based change detection in `checklist.md`.
- **Rationale**: Prevents redundant processing of unmodified files while allowing automatic re-transcription if an audio file is updated.

## 4. Atomic State Persistence
- **Decision**: Checklist updates occur *after* file flushing.
- **Rationale**: Ensures that a crash during processing does not result in a "False Positive" completion status.

## 5. Configuration via JSON (`config.json`)
- **Decision**: Use `config.json` rather than markdown (`models.md` / `prompts.md` for models) to define phase specifications.
- **Rationale**: JSON perfectly maps to Python dictionaries without custom regex parsing. It cleanly handles nested structures like `options` (temperature, num_ctx), and enables defining multiple test "profiles" in a single file effortlessly.

## 6. Global Unification of `checklist.md`
- **Decision**: Maintain a single `voice-memo/checklist.md` grouped by *Subject*, ignoring dispersed subject-specific checklists.
- **Rationale**: Prevents directory pollution inside `audio/` folders. It acts as a single pane of glass for all tasks context and removes repetitive file searching and I/O spread across directories.

## 7. Open Claw Skill Transformation
- **Decision**: Re-house all python operations under `skills/voice-memo/scripts/` and delete `py_tools/`.
- **Rationale**: Elevates the raw python scripts into an orchestrated "Open Claw Skill". A `SKILL.md` is provided at the root of `skills/voice-memo` so that an LLM proxy (such as a Telegram bot) has actionable instructions and access to trigger the components conversantly without the user needing to manually run terminal commands.

## 8. Apple Silicon MPS Native Optimization
- **Decision**: Shift primary execution out of Docker directly into the host OS (macOS), leveraging `mlx-whisper` dynamically inside Phase 1.
- **Rationale**: Docker creates an invisible Linux virtualization layer on Apple machines that completely isolates and shuts off access to the Metal Performance Shaders (MPS), throttling transcribe performance drastically. Running natively circumvents virtualization bottlenecks while complying perfectly with the LLM Sandbox logic (which strictly patrols file-edit radii without blocking underlying processor hardware calls).

## 9. Local-First AI Git Syncing
- **Decision**: Force the AI agent to automatically trigger local `git commit` actions and sync 6 core MD files upon task completion.
- **Rationale**: Acts as a frictionless rollback layer for the MacBook environment without needing a remote Github repository. It empowers the developer to confidently test code knowing the agent has snapshotted the prior stable state.



## 10. Batch Selection & Checkpoint Resume UI
- **Decision**: Replace sequential Y/N input prompts and silent task skipping with an interactive text UI list for reprocessing, while introducing a Checkpoint tracker in `.pipeline_state.json`.
- **Rationale**: In batch operations of multiple files, asking users Y/N for each skipped file causes extreme fatigue and prevents autonomous execution. Silently skipping them causes confusion ("did it run at all?"). Rendering an interactive batch selector *before* `tqdm` bars start resolves I/O clashing. Additionally, providing Checkpoint resumption guarantees users can recover half-finished pipelines caused by hardware crashes or intentional interrupts without wasting prior computation time.

---

## 🤖 Antigravity Execution History (Implementation Plans)

### 🕒 [2026-04-02 01:53] Phase 1 - Voice Transcription & Notion Export System Analysis & Refactoring
Optimized duplicate logic and hardcoded parameters. Unified `OLLAMA_API` and `requests.post` sending logic into `subject_manager`, and added a unified robust `sm.should_process_task` retry control step. Established a Markdown formatted `models.md` to extract model variables away from the code base.

### 🕒 [2026-04-02 04:38] Phase 2 - 進階系統優化與重構計畫 (Production Grade Upgrade)
### 🕒 [2026-04-02] Phase 3/4 - Directory Restructure & Universal Prompts
- **Decision**: Rename root operational directories (`raw_data`, `transcript`, `proofread`, `notion_synthesis`).
- **Rationale**: Removes misleading context (like `audio`).
- **Decision**: Dual `.md` output in transcription.
- **Rationale**: While `.vtt`/`.srt` are standard, outputting Markdown (`[0:00] - [0:30] ...`) ensures frictionless processing through LLMs without stripping HTML-like timecode elements. This provides both human-readable timelines and high AI utility.

### 🕒 [2026-04-02] Phase 5 - Notion Synthesis Context Isolation
- **Decision**: Programmatically strip `## 📋 彙整修改日誌` from Phase 2 contents before sending to Phase 3.
- **Rationale**: LLMs mistakenly interpret the log component from the input as conversational chatter or system logs. To synthesize an academic document faithfully without conversational filler, only the transcript must be embedded in the context window.

### 🕒 [2026-04-02] Phase 6 - Prompt Encapsulation 
- **Decision**: Remove strict formatting guardrails from Python (`notion_synthesis.py`) and centralize them into `prompt.md`.
- **Rationale**: Hardcoding prompts inside Python violates the architecture rule of using `prompt.md` to cleanly separate logic from instruction design. This ensures the prompt can be modified universally in a single text file.

### 🕒 [2026-04-02] Phase 7 - Strict Context Injection (Middle-Lost Fix)
- **Decision**: Use an `{INPUT_CONTENT}` placeholder in `prompt.md` and explicitly place the `CRITICAL FORMAT REQUIREMENT` at the absolute bottom of the document.
- **Rationale**: When feeding long transcripts (often >10,000 chars), LLMs commonly suffer from the "Lost in the Middle" phenomenon where they forget the strict parsing behavior dictated at the very top of the prompt. Injecting the transcript in the middle and appending the format instructions at the very end heavily bounds the model's immediate output attention window.

### 🕒 [2026-04-02] Phase 8 (Reroll) - Descriptive Hierarchy Flattening
- **Decision**: Flatten the nested Phase 3 output requirements (A/B/C) into top-level numbered lists (1-7), inject uppercase `(DO NOT SKIP)` warnings, and add explicit Mermaid and Hashtag descriptive rules. Remove the hardcoded Markdown templates.
- **Rationale**: The previous architectural attempt to force a literal Markdown template (alongside config context window injections) was over-engineered and caused systemic fragility. The LLM ignored Feynman/Cornell originally because of deep list nesting (1. > 4. > A.), which causes smaller models (like Gemma 3) to lose track of instruction depth and summarize the group as a single paragraph. Flattening the hierarchy resolves this cleanly while adhering to the original system boundaries established in Phase 7.

### 🕒 [2026-04-02] Phase 11 - Open Claw Skill Integration
- **Decision**: Port `py_tools` into an interactive Open Claw Skill setup.
- **Rationale**: Ensures the user can launch any portion of the Voice Memo workflow from Telegram just by chatting with their AI agent.

### 🕒 [2026-04-02] Phase 12 - MPS Hardware Acceleration Update
- **Decision**: Implant `mlx-whisper` to replace `faster-whisper` as an opt-in profile variant for Mac users. Implement `unload_ollama_model()`.
- **Rationale**: `faster-whisper` operates on CTranslate2, which inherently lacks MPS support. Switching to `mlx` bypasses this barrier and directly taps M-Series unified memory architecture for exponential transcription boost. Active unloading protects macOS hardware from VRAM starvation.

### 🕒 [2026-04-02] Phase 13 - Asynchronous Progress UI Evolution
- **Decision**: Architect a multi-threaded `tqdm` polling loop utilizing `threading.Event` to govern progress bars for synchronous model requests (`mlx-whisper` and bulk `Ollama` generations), unifying UX across the entire pipeline.
- **Rationale**: Originally, `faster-whisper` supported perfect ETA tracking due to its generator-based streaming array. However, synchronous libraries (`mlx-whisper` and blocking Ollama APIs) natively starve the main thread, resulting in terminal freeze states that prompt users to execute panic interrupts (SIGINT), triggering multiprocess semaphore memory leaks. An initial attempt injected `verbose=True` to stream text logs locally, but this polluted standard output. Engineering a detached daemon loop to asynchronously refresh a headless `tqdm` bar entirely bypasses architectural bottlenecks across all Phase 1, 2, and 3 models, visually assuring users via a clean ticking execution-timer without generating standard output garbage.

### 🕒 [2026-04-02] Phase 14 - Host Environment Hardening & Storage Isolation
- **Decision**: Eradicate global absolute paths in `transcribe_tool.py` and actively inject `HF_HOME`/`HF_HUB_CACHE` environment variables mapped relative to `sm.WORKSPACE_ROOT`. Additionally, replace Docker network endpoints (`host.docker.internal`) with static Mac Loopbacks (`127.0.0.1`).
- **Rationale**: As the project evolved beyond a containerized Linux Docker environment into native Apple macOS execution, legacy volume paths (such as `download_root="/models"`) provoked severe `OSError [Errno 30] Read-only file system` kernel security rejections. By intercepting HuggingFace environmental configs right before module loading, we structurally quarantine multi-gigabyte monolithic neural network weights into the sterile, user-accessible directory: `open-claw-workspace/models/`. This prevents latent fragmentation of the user's root disk space (e.g., `~/.cache/huggingface/`) and empowers friction-free systemic uninstalls, as witnessed by the seamless rollback out of `mlx-whisper` to efficiently reclaim gigabytes of storage density. Furthermore, the deprecation of Docker virtualization mandated shifting Ollama endpoints directly to `127.0.0.1` to cure systemic `NameResolutionError` TCP connection outages strictly isolated to native host routing.

### 🕒 [2026-04-02] Phase 15 - Hardware Defense Metrics Optimization
- **Decision**: Override the unified RAM exhaustion limits in `subject_manager.py` specifically for macOS Darwin architectures, dropping Warning flags from `4000MB` to `1024MB` and Critical Force Close flags from `2048MB` to `300MB`.
- **Rationale**: When heavily demanding Local LLMs (e.g., `gemma3:12b` needing ~8-10GB RAM) were forced to operate simultaneously with the Python CLI naturally on the macOS Localhost, available RAM swiftly plunged to ~1GB, triggering false-positive `[RAM 耗盡]` (RAM Exhaustion) safety locks. Given macOS possesses inherently superior Unified Memory and dynamic Swap Disk mechanisms, retaining the strict `2048MB` threshold completely neutered the Mac's capability to safely infer large context phases. Relaxing this barrier ensures the system utilizes maximum compute potential before executing terminal safeguards.

### 🕒 [2026-04-03] Phase 16 - File Progress Counter & Phase 2 Segment Merger
- **Decision**: Pre-filter `pending_tasks` by calling `should_process_task()` before the main loop, then use `enumerate(pending_tasks, start=1)` to display `[X/Y]` counters in terminal logs across all three Phase scripts.
- **Rationale**: Previously, the loop iterated over all tasks and skipped completed ones inline. Users had no way to know how many files were actually queued for the current run. By pre-filtering, we obtain an accurate `total` count before any work starts, enabling a meaningful `[1/3]` style display that eliminates uncertainty during long batch runs.

- **Decision**: Implement automated segment detection and post-completion merging in Phase 2 via `get_lecture_base()` (regex parser), `group_tasks_by_lecture()` (grouper), and `merge_proofread_segments()` (merger) functions in `proofread_tool.py`.
- **Rationale**: Lectures recorded in multiple segments (e.g., `L01-1.m4a`, `L01-2.m4a`) were previously proofread into separate disconnected files. This fragmented the source material for Phase 3 synthesis, forcing the LLM to process incomplete context. By automatically merging all segments into a single `L01_merged.md` (complete corrected body + unified modification log) immediately after all segments complete, we provide Phase 3 with coherent, full-lecture input. Individual segment files are preserved for traceability.

### 🕒 [2026-04-07] Phase 16 (V5.0) — Five-Phase Pipeline Refactor (Separation of Concerns)

- **Decision**: Expand the pipeline from 3 phases to 5 dedicated phases, each with its own output directory (`01_transcript/` → `05_notion_synthesis/`), dedicated `prompt.md` section, and dedicated `config.json` profile.
- **Rationale**: The original 3-phase design conflated proofreading, merging, and synthesis into too few steps. This caused LLM context pollution: the model tried to simultaneously "correct errors", "merge segments", and "structure speakers" in one pass, leading to accumulated errors and hallucination. Enforcing Separation of Concerns means each LLM call has exactly one job, drastically improving per-phase accuracy.

- **Decision**: Phase 2 (`proofread_tool.py`) is stripped to a **pure 1:1 verbatim corrector**. All segment merging is moved to Phase 3.
- **Rationale**: When Phase 2 also merged segments, the LLM was forced to simultaneously correct terminology AND restructure conversation flow AND infer speaker identity — three fundamentally different tasks. Isolating correction from restructuring lets Phase 2 achieve near-perfect terminological accuracy without distraction.

- **Decision**: Phase 4 (`highlight_tool.py`) anti-tampering threshold set at **>5% character reduction** (not the initially suggested 10%) triggers fallback to the original chunk.
- **Rationale**: The initial plan suggested 10%. Testing showed that even at 5% reduction, the LLM was already silently paraphrasing or summarizing short sentences. A stricter 5% guard is necessary to enforce the "zero deletion" contract reliably on smaller models like `gemma3:12b`. The fallback preserves content at the cost of losing some highlights for that chunk, which is the correct trade-off for verbatim integrity.

- **Decision**: `run_all.py` orchestrator created with three flags: `--interactive` (human-in-the-loop pause after each phase), `--from N` (resume from phase N), `--force` (ignore ✅ checklist status).
- **Rationale**: Users needed a single command to run the full pipeline without manually invoking 5 scripts. `--interactive` addresses the human review checkpoint need identified in the Enhancement Plan, where a wrong Phase 3 merge propagating through Phase 4 and 5 would otherwise be undetectable before it's too late.

### 🕒 [2026-04-08] Phase 17 — Glossary Injection & Phase Responsibility Boundary

- **Decision**: Add `raw_data/<subject>/glossary.json` — a per-subject flat key-value map (`{whisper_misrecognition: correct_academic_term}`) — and a `subject_manager.get_glossary(subject)` utility that reads and formats it for LLM injection.
- **Rationale**: Whisper has no domain vocabulary; it consistently mishears academic jargon (e.g., `「折中」` instead of `「折衷」`, `「EST」` unresolved). Injecting a user-curated glossary as a side-channel reference into Phase 2's prompt gives the LLM an explicit correction table, eliminating recurring misrecognitions without retraining. Graceful degradation (silent skip if file absent) ensures no breaking change.


- **Decision**: Assign data quality responsibilities to phases strictly by their data access rights:
  - **Phase 2** = verbatim correction + term normalization (glossary) + data integrity (PDF-grounded — `audio_value ≠ pdf_value → use pdf_value`)
  - **Phase 3** = structural transformation + oral filler denoising + pronoun/subject recovery (corpus-grounded, full merged lecture available)
  - **Phase 4** = non-destructive Markdown emphasis only (zero content change mandate)
- **Rationale**: Phase 3 does not receive the PDF as input. Therefore, any rule requiring PDF-vs-audio comparison (Data Integrity) *must* be enforced in Phase 2 while PDF context is still available. Moving it to Phase 3 would require passing PDF paths forward, adding complexity and breaking the `concerns must not bleed between phases` principle. Similarly, oral filler denoising belongs in Phase 3 (not Phase 2) because Phase 2's mandate is *verbatim fidelity* — removing fillers at that stage would destroy the proofreading audit trail.

### 🕒 [2026-04-08] Phase 18 — Bug Fix Design Decisions

- **Decision**: Fix `transcribe_tool.py` to write `text_val.strip() + "\n"` instead of `text_val` for the non-timestamped transcript.
- **Rationale**: The original code concatenated all Whisper segment texts into a single string with no separator, producing a 40KB+ wall of text on line 1. This caused two downstream problems: (1) chunk boundaries would split English words mid-character (e.g., `action taki\nng`), producing broken text that Phase 2 could not correct reliably; (2) the wall of text gave the LLM no natural paragraph structure to anchor corrections. The timestamped version was already per-line, making the discrepancy a pure oversight. Fix: identical segment separator (newline) as timestamped, matching Whisper's natural segment boundaries which are semantically cleaner split points than character-count boundaries.

- **Decision**: Implement a deduplication guard in `proofread_tool.py`'s change log assembly that (a) strips repeated `Explanation of Changes:` / `彙整修改日誌` headers, and (b) skips any log entry identical to the immediately preceding entry.
- **Rationale**: Discovered in `02_proofread/助人歷程/L02-1.md` that the LLM wrote `equip → equip` (no actual change, identical before/after) 120+ times in a row, and each of the 9 chunks generated its own `## Explanation of Changes:` header. Root cause: the LLM's context window end-of-chunk repetition hallucination was not guarded against. A simple line-deduplication guard at the Python level (not asking the LLM to self-correct) is the lowest-risk solution — it requires no prompt change and cannot introduce new errors. The `before ≠ after` rule added to the prompt further discourages no-op entries upstream.

- **Decision**: Phase 3 (`merge_tool.py`) now parses and accumulates a `## 📋 Phase 3 修改日誌` change log identically to Phase 2, and appends it to the merged output file.
- **Rationale**: Phase 2 had a full audit log to enable human review of LLM corrections. Phase 3's denoising and rewriting operations (oral filler removal, pronoun resolution, numerical normalisation) are equally impactful but were previously invisible — there was no way to verify that Phase 3 had not hallucinated content. Adding a Phase 3 audit log closes this accountability gap. The log is labelled `Phase 3 修改日誌` explicitly to distinguish it from the Phase 2 log, preventing confusion during manual review. The `p3_log_items` variable initialisation fix (before the chunk loop) ensures correct behaviour when no LLM changes are made for a given chunk.

### 🕒 [2026-04-09] Phase 19 — Full Pipeline Review & Code Quality Hardening

- **Decision**: Replace raw character-slice chunking (`text[i:i+chunk_size]`) with `sm.smart_split(text, chunk_size)` in Phase 2, Phase 3, and Phase 4.
- **Rationale**: Raw character slicing produced chunk boundaries inside English words (eg `action taki` / `ng`), Chinese sentences, or academic terms. While the Phase 1 newline fix reduced word-split frequency, it did not eliminate it — a paragraph may still exceed chunk_size if the audio recording is dense. `smart_split()` respects `\n` boundaries, only falling back to hard cuts when a single paragraph is longer than chunk_size. This preserves sentence integrity at chunk boundaries for all three LLM phases.

- **Decision**: Increase Phase 2 `chunk_size` from 2000 to 3000 characters.
- **Rationale**: Chinese text has 1 character = 1 Unicode code point; an English sentence of 10 words is already ~60 characters. At 2000 chars, a Chinese lecture transcript of 600-1000 characters per minute generates 30+ chunks per file, each with too little context for the LLM to understand paragraph semantics. 3000 chars gives approximately 1000 Chinese characters per chunk — enough for 1-2 coherent lecture paragraphs without overwhelming the context window.

- **Decision**: Strip `## 📋 Phase 3 修改日誌` from Phase 4's input, highlight only the body, then re-attach the log to Phase 4's output.
- **Rationale**: Phase 4 reads the full output of Phase 3 (including the audit log). Without stripping, the LLM was asked to highlight log entries like `* **"原文"** → **"修正後"** — 理由`, which are metadata — not content. This caused: (1) unnecessary highlighting of log entries; (2) potential accidental truncation of log entries by the anti-tampering guard; (3) bloating of Phase 4's context window. Re-attaching the log post-highlight preserves full audit traceability through Phase 4 and into Phase 5.

- **Decision**: Add Qwen2.5:14b and Qwen3:14b as opt-in alternative profiles in `config.json` for Phase 2, 3, 4, and 5.
- **Rationale**: `gemma3:12b` is Google's general-purpose model with an English-dominant training corpus. For Traditional Chinese academic text (which contains domain jargon, mixed Chinese/English, and colloquial lecture speech), Alibaba's Qwen series — trained on 18T tokens including extensive Chinese data — has materially stronger vocabulary coverage, tone recognition, and instruction adherence in Chinese. Qwen3:14b also supports a `thinking` mode that can be disabled for speed. To avoid disrupting existing workflows, Qwen profiles are added as **opt-in alternatives** — users must change `active_profile` in `config.json` to switch. No existing pipeline behaviour changes by default.

### 🕒 [2026-04-12] Phase 20 — V7.0 Deep Architecture Upgrade (OOP & DAG Cascade)

- **Decision**: Eradicate procedural script redundancy by extracting a universal Object-Oriented Framework base `core/` (comprising `pipeline_base.py`, `state_manager.py`, `llm_client.py`).
- **Rationale**: Prior to V7.0, all 6 scripts shared over 60% identical boilerplate logic (Hardware scanning, Interrupt trapping, Tqdm UI polling, Ollama API networking). The tight coupling violated DRY principles. Moving IO logic into `core/pipeline_base.py` allows scripts to purely concentrate on `Phase` specific LLM instruction and routing sets.

- **Decision**: Redesign the entire Task Checklist state tracker into an invisible local database (`.pipeline_state.json`) governed by DAG (Directed Acyclic Graph) Hash State Tracking. `checklist.md` is strictly relegated to a UI View.
- **Rationale**: The previous `checklist.md` system was flawed because modifying a Phase 2 output mathematically required re-running Phase 3, 4, and 5. But because the system relied on manual user flags (`--force`) and binary `✅` checks instead of File Identity, users were risking output mismatch. Enforcing SHA-256 Hash tracking directly ties the downstream status to the output hash. A human editing a Markdown file instantly causes the Hash to invalidate, inherently triggering a **Cascade Invalidation** that marks subsequent tasks as `⏳` organically.

- **Decision**: Imbed Agentic Mermaid Retry validation specifically inside Phase 5 `notion_synthesis.py`.
- **Rationale**: Even with explicit prompt tuning, smaller local models (like `gemma3:12b`) occasionally regress on complex multi-tier payload schemas and output corrupted markdown chunks (like forgetting the `mindmap` component of Mermaid). Injecting an agentic loop effectively commands the LLM to recursively review its output and parse corrections internally within 2 timeout thresholds, insulating the Notion user from visual formatting flaws globally without causing immediate run termination.

### 🕒 [2026-04-14] Phase 20 - UX Batch UI & Checkpoints (V7.1)
- **Decision**: Embed `pause_requested` signals and Checkpoint passing (as `resume_from` objects) deeply into the OOP framework instead of treating it as a global flag script side.
- **Rationale**: To retain Separation of Concerns under V7.0, Phase Logic scripts must only concern themselves with running the pipeline. Moving the Checkpoint tracking/Y/N user input entirely into `PipelineBase.get_tasks` prevents duplicating UI code across 5 python scripts.
