# HEARTBEAT.md

## Operational Heartbeat Checklist

Run this checklist at the start of any agent session to confirm workspace health.
Respond with `HEARTBEAT_OK` if all checks pass with no action required.

### 1. Log Health
- [ ] No unresolved `ERROR` or `CRITICAL` entries in `data/voice-memo/logs/system.log`
- [ ] No unresolved `ERROR` or `CRITICAL` entries in `data/pdf-knowledge/logs/system.log`
- [ ] No unresolved `ERROR` entries in `data/pdf-knowledge/logs/dashboard.log`

### 2. Resume State
- [ ] No stale interrupted states in `data/voice-memo/state/.pipeline_state.json`
- [ ] No unexplained interrupted sessions in `data/pdf-knowledge/state/resume/*/resume_state.json`

### 3. Documentation Parity
- [ ] All recent code changes have corresponding documentation updates
- [ ] No skill SKILL.md references a script path that no longer exists
- [ ] No HANDOFF.md references a state that has since changed

### 4. Task Status
- [ ] Review `skills/voice-memo/docs/TASKS.md` for blocking items
- [ ] Review `skills/pdf-knowledge/docs/TASKS.md` for blocking items

### 5. Sandbox Boundary
- [ ] No new code in skills references paths outside `open-claw-sandbox/`
- [ ] No new log routes added outside `data/<skill>/logs/`
