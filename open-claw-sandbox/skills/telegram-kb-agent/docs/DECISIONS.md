# DECISIONS.md — Telegram KB Agent Skill

> Technical decision log for the `telegram-kb-agent` skill.

---

## 2026-04-22 — Single Bot Token Enforcement (PID Lock)

**Decision**: The bot daemon creates a `.bot.pid` lock file on startup and exits immediately
if the file already exists (containing a running PID).

**Context**: Telegram's Bot API supports only one active Long Polling connection per bot token.
If two `bot_daemon.py` instances start simultaneously (e.g., `start.sh` called twice), both
will appear to receive messages but only one will actually send replies — the other will get
`409 Conflict` errors from Telegram, causing silent message loss.

**Chosen approach**: PID lock at `data/telegram-kb-agent/.bot.pid`. On startup, check if the
PID in the file refers to a running process (`os.kill(pid, 0)`). If yes, exit with an error.
If no running process, overwrite the lock and start. On clean exit, remove the lock file.

**Trade-off**: If the daemon crashes (OOM, SIGKILL), the stale PID file must be manually removed.
Considered a reasonable operational trade-off vs. silent message loss.

---

## 2026-04-22 — RAG-Only Responses (Never Pure LLM)

**Decision**: All bot responses must be generated from retrieved ChromaDB passages.
If no relevant passages are found (`top_k=5` returns empty), respond with a "no relevant notes"
message rather than generating an answer from LLM general knowledge.

**Context**: The user's Telegram bot is trusted to answer questions about their **personal**
academic notes. An answer from LLM general knowledge would be indistinguishable from an answer
grounded in the user's actual notes, leading to false confidence.

**Chosen approach**: The retrieval step always runs first. If `len(retrieved_passages) == 0`,
return: "I couldn't find relevant content in your notes for this query."

**Trade-off**: The bot cannot answer questions about topics not yet in the wiki vault.
Acceptable — the user knows what they've indexed.

---

## 2026-04-22 — `top_k=5` Retrieval Limit

**Decision**: Retrieve at most 5 semantic passages from ChromaDB per query.

**Context**: `gemma3:12b`'s effective context window for high-quality synthesis is approximately
4,000–6,000 tokens. An average wiki note passage is ~200–300 tokens. 5 passages (~1,500 tokens)
leaves sufficient room for the system prompt and response.

**Chosen approach**: `top_k=5` is hardcoded in the retrieval call. Configurable via `config.yaml`
for environments with larger models.

---

## 2026-04-22 — Telegram as HITL Notification Channel

**Decision**: Route all `HITLPendingInterrupt` alerts and `/hitl approve` commands through the
existing Telegram bot daemon rather than building a separate notification service.

**Context**: The user already monitors Telegram. Adding a second notification channel (email, webhook)
would fragment attention and increase operational complexity.

**Chosen approach**: When `HITLPendingInterrupt` is raised by a pipeline phase, `core/services/hitl_manager.py`
calls `core/services/telegram_bot.py` to send an alert. The user replies `/hitl approve <trace_id>`.
The bot handler writes the approval signal to `core/state/<trace_id>.resume` and the polling pipeline resumes.

**Trade-off**: If Telegram is unavailable (network outage), HITL pipelines will be permanently
stalled until manually resumed. Mitigation: pipelines have a `hitl_timeout` (default 24h) after
which they auto-cancel with a log entry.
