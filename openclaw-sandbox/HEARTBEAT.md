# HEARTBEAT.md

## Operational Heartbeat Checklist

Run this checklist at the start of any agent session to confirm workspace health.
Respond with `HEARTBEAT_OK` if all checks pass with no action required.

### 1. Log Health
- [ ] No unresolved `ERROR` or `CRITICAL` entries in `data/audio_transcriber/logs/system.log`
- [ ] No unresolved `ERROR` or `CRITICAL` entries in `data/doc_parser/logs/system.log`
- [ ] No unresolved `ERROR` or `CRITICAL` entries in `data/inbox_manager/logs/system.log`

### 2. Resume State
- [ ] No stale interrupted states in `data/audio_transcriber/state/.pipeline_state.json`
- [ ] No unexplained interrupted sessions in `data/doc_parser/state/.pipeline_state.json`
- [ ] No stale HITL checkpoints in `core/state/`

### 3. Documentation Parity
- [ ] All recent code changes have corresponding documentation updates
- [ ] No skill SKILL.md references a script path that no longer exists
- [ ] No HANDOFF.md references a state that has since changed

### 4. Task Status
- [ ] Review `memory/TASKS.md` for blocking items globally

### 5. Sandbox Boundary
- [ ] No new code in skills references paths outside `openclaw-sandbox/`
- [ ] No new log routes added outside `data/<skill>/logs/`
