# HEARTBEAT.md

## Operational Heartbeat Checklist

Run this checklist at the start of any agent session to confirm workspace health.
Respond with `HEARTBEAT_OK` if all checks pass with no action required.

### 1. Log Health
- [ ] No unresolved `ERROR` or `CRITICAL` entries in `data/audio_transcriber/logs/system.log`
- [ ] No unresolved `ERROR` or `CRITICAL` entries in `data/doc_parser/logs/system.log`
- [ ] No unresolved `ERROR` or `CRITICAL` entries in `data/proofreader/logs/system.log`
- [ ] No unresolved `ERROR` or `CRITICAL` entries in `data/inbox_manager/logs/system.log`

### 2. Resume State
- [ ] No stale interrupted states in `data/audio_transcriber/state/.pipeline_state.json`
- [ ] No unexplained interrupted sessions in `data/doc_parser/state/.pipeline_state.json`
- [ ] No stale HITL checkpoints in `core/state/`
- [ ] No orphaned `pending_chains.json` files in `data/proofreader/output/pending_chains/` (files here mean the watchdog did not resume)
- [ ] `data/student_researcher/input/` staging area reviewed — if files are present, confirm user intends to manually trigger

### 3. Documentation Parity
- [ ] All recent code changes have corresponding documentation updates
- [ ] No skill SKILL.md references a script path that no longer exists
- [ ] No HANDOFF.md references a state that has since changed

### 4. Task Status
- [ ] Review `memory/TASKS.md` for blocking items globally

### 5. Sandbox Boundary
- [ ] No new code in skills references paths outside `openclaw-sandbox/`
- [ ] No new log routes added outside `data/<skill>/logs/`

### 6. V9.17 Architecture Invariants
- [ ] All new skill phases use `self.info/self.error/self.warning` (never bare `print()`)
- [ ] No skill phase instantiates `OllamaClient()` directly (must reuse `self.llm` from `PipelineBase`)
- [ ] `student_researcher` is NOT in any automated routing chain (manual trigger only)
- [ ] Sequential SSoT Chain order respected: `smart_highlighter` ➔ `note_generator` ➔ `feynman_simulator` ➔ `academic_edu_assistant`
