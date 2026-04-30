# DECISIONS.md — Inbox Manager Skill

> Technical decision log for the `inbox-manager` skill.

---

## 2026-04-19 — inbox-manager as a Standalone Skill (not a core/ utility)

**Decision**: Implement inbox routing rule management as a separate `skills/inbox-manager/`
rather than a sub-command of `core/inbox_daemon.py`.

**Context**: `inbox_daemon.py` is a long-running background process. Adding interactive
CLI commands directly to it would require daemon restarts for simple rule lookups, which
defeats the purpose of a background service.

**Chosen approach**: `inbox-manager` is a stateless CLI skill that reads and writes
`core/config/inbox_config.json` directly. Since `inbox_daemon.py` hot-reloads the
config on every file event, changes take effect within seconds without any restart.

**Impact**: Operators can manage routing rules while the daemon is running, with zero
service interruption.

---

## 2026-04-19 — Routing Mode Enum: `audio_ref`, `doc_parser`, `both`

**Decision**: The routing mode field in `inbox_config.json` uses exactly three string values:
`audio_ref`, `doc_parser`, `both`.

**Context**: An early design considered a bitmask integer (1=audio_ref, 2=doc_parser, 3=both).
String enums were chosen for human readability in the JSON config file.

**Chosen approach**: `inbox_daemon.py` branches on these exact string values. The `inbox-manager`
CLI validates that any `--routing` argument matches one of the three allowed values.

**Critical**: If you rename these strings, you MUST update `inbox_daemon.py` simultaneously.
The strings are not centralized in a Python enum — they are matched by literal string comparison.

---

## 2026-04-19 — Hot-Reload Without Daemon Restart

**Decision**: `inbox_daemon.py` re-reads `inbox_config.json` on every `watchdog` file-system
event, not once at startup.

**Context**: If routing rules were loaded once at daemon startup, adding a new rule would require
killing and restarting the daemon — a multi-second interruption that risks missing incoming files.

**Chosen approach**: `inbox_daemon.py`'s event handler calls `_load_config()` at the start of
every processing cycle. The JSON parse overhead is negligible (~1ms) and ensures rules are
always current.

**Trade-off**: A malformed `inbox_config.json` will cause every file event to fail until corrected.
`AtomicWriter` mitigates this — partial writes never corrupt the file.
