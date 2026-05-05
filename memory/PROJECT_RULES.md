# System Context & Development Contract

> **Target Audience:** Development AIs (Google Antigravity, Claude Code, GitHub Copilot)
> **Purpose:** Defines the active hardware constraints, End-of-Feature protocol, and Documentation update rules for the workspace.
> **Last Updated:** 2026-05-05

## 1. Environment Constraints

- **OS**: macOS Apple Silicon
- **Hardware**: 16 GB RAM (Strict memory limits apply — strictly one heavy model at a time. Watchdog evicts models if memory threshold is exceeded)
- **Primary Language**: Code in English, Communication in Traditional Chinese.
- **Tech Stack**: Python 3.9+, Ollama, MLX-Whisper, Docling, ChromaDB, LiteLLM, Telegram Bot API
- **Execution Environment**: Headless CLI-first with Ephemeral WebUI gates for Human-in-the-Loop verification.

## 2. Mandatory Workflow

Every AI agent must follow this sequence upon startup to ensure zero context loss:

1. Read `memory/PROJECT_RULES.md` (this file)
2. Read `memory/HANDOFF.md` to understand current state
3. Read `memory/TASKS.md`
4. Read `docs/STRUCTURE.md` for the annotated map of every file and folder
5. Read `identity/AI_PROFILE.md` and `open-claw-sandbox/AGENTS.md` for specific agent behaviours
6. Read `skills/<skill>/SKILL.md` if executing a specific skill
7. Begin execution

## 3. Strict Prohibitions (NEVER DO THESE)

- **Do NOT** execute destructive commands (`rm -rf`) or take external actions (email, public posting) without explicit operator approval.
- **Do NOT** leak private data outside the local sandbox boundary (`open-claw-sandbox/`).
- **Do NOT** leave placeholder text (e.g. "insert logic here") or partial implementations. Write complete code.
- **Do NOT** truncate code or logs. Preserve 100% of the content (**Anti-Truncation Protocol**).
- **Do NOT** modify `DECISIONS.md` history or delete past task logs. Always append or mark as `[ABANDONED]`.
- **Do NOT** use `print()` for debugging in production code. Always use `core.utils.log_manager` or `rich`.
- **Do NOT** modify `.env` or files containing real credentials.
- **Do NOT** push directly to `main` without verification.

## 4. Documentation Update Requirement & Auto-Evolution

If code changes affect observable behavior, or if **a new rule/habit is discovered during the conversation**, you MUST automatically update the corresponding documentation. Never write rules to random files. Follow this strict routing table:

| Changed behaviour / New Rule Discovered | Exact File to Update |
|:---|:---|
| Operator preferences, prompt macros, communication style | `identity/AI_PROFILE.md` |
| New programming standard, syntax rule, code pattern | `docs/CODING_GUIDELINES.md` |
| IDE workspace limits, end-of-task protocols | `memory/PROJECT_RULES.md` |
| Local Sandbox Agent boundaries or system ethics | `open-claw-sandbox/IDENTITY.md` or `SOUL.md` |
| Architectural decision made (Why X over Y) | `memory/DECISIONS.md` + `skills/<skill>/docs/DECISIONS.md` |
| Data path, phase logic, or core module change | `docs/STRUCTURE.md` + `skills/<skill>/docs/ARCHITECTURE.md` |
| CLI interface or user-facing operation change | `skills/<skill>/SKILL.md` + `docs/USER_MANUAL.md` |

## 5. End-of-Feature Protocol (完工標準作業流程)

Whenever a feature, bug fix, or major task is completed, you MUST perform the following steps before declaring the task finished:

1. **Verify Correctness**: Run specific `pytest` tests or manually test the updated module.
2. **Quality Gate**: Run `cd open-claw-sandbox && ./ops/check.sh` to ensure `ruff` linting/formatting and `mypy` type-checking pass without errors.
3. **Global SSoT Sync**: Ensure all relevant Markdown files (Architecture, Manuals, Structure) are updated.
   - *Continuous Principle Sync*: If any new operational principles, constraints, or workflow habits were discovered or established during this session, you MUST immediately update `identity/AI_PROFILE.md` or `docs/CODING_GUIDELINES.md` to permanently record them.
   - *Principle Acknowledgement*: Every newly captured rule MUST be confirmed in-conversation with the format: `✅ 原則已記錄 → [file.md]：<content>`
4. **Version Control**: Stage changes (`git add -A`), write a conventional commit message, and push to the GitHub repository (`git push`).
5. **Session Archival**: Run `python3 ops/archive_session.py` **AFTER** `git push` (not before) to ensure the full conversation including archival confirmation is captured. Update `memory/HANDOFF.md` & `memory/TASKS.md`.

> [!IMPORTANT]
> `archive_session.py` MUST run after `git push`, never before. The archival log may miss the final conversation turns if run before pushing.

---

## 6. Code Review Checklist (每次深度審查必跑)

When performing a full code audit (triggered by "讀取 AI_PROFILE.md，深度分析..."), the AI MUST systematically check every item below in addition to running `./ops/check.sh`:

| # | Check | Command / Method |
|:---:|:---|:---|
| 1 | No bare `print()` in production code | `grep -r "^print(" core/ skills/` |
| 2 | No hardcoded file paths | `grep -rn '/data/raw\|/tmp/openclaw' core/ skills/` |
| 3 | All LLM calls followed by `unload_model()` | Manual review of each `llm.generate()` callsite |
| 4 | All file writes use `AtomicWriter` | `grep -rn "open(.*[\"']w[\"']" core/ skills/` |
| 5 | All config reads go through `config_manager` | `grep -rn "yaml.load\|json.load.*config" core/ skills/` |
| 6 | DRY compliance — no duplicated for-loop logic | Semantic review across Phase scripts |
| 7 | `STRUCTURE.md` matches actual directory tree | `ls` vs documented structure |
| 8 | `HANDOFF.md` timestamp is current | Check `Last Updated` field |
| 9 | No `# TODO` without accompanying issue reference | `grep -rn "# TODO" core/ skills/` |
| 10 | All new principles captured and confirmed | Review conversation for `✅ 原則已記錄` markers |

