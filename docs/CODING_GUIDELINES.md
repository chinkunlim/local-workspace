# Open Claw Engineering Standards

> **Version:** v4.0.0 (2026-05-01 — Global English Translation & Core Sub-Package Update)
> **Scope:** All developers and AI agents operating in `local-workspace/`
> **Tools:** Ruff, Mypy, Shellcheck, pytest
> **Philosophy:** Simple, Robust, Traceable, AI-Friendly

---

## Table of Contents

1. [AI Agent Mandatory Workflow](#1-ai-agent-mandatory-workflow)
2. [Code Quality Principles](#2-code-quality-principles)
3. [Architecture & Design](#3-architecture--design)
4. [Error Handling & Defensive Programming](#4-error-handling--defensive-programming)
5. [Open Claw-Specific Invariants](#5-open-claw-specific-invariants)
6. [Python Style & Formatting](#6-python-style--formatting)
7. [Type Annotations](#7-type-annotations)
8. [Logging Standards](#8-logging-standards)
9. [Testing Standards](#9-testing-standards)
10. [Git & Version Control](#10-git--version-control)
11. [Security](#11-security)
12. [Documentation Standards](#12-documentation-standards)
13. [Prohibited Patterns](#13-prohibited-patterns)
14. [Quick Reference](#14-quick-reference)

---

## 1. AI Agent Mandatory Workflow

> ⚠️ **All AI Agents must complete the following steps in order before executing any task. Skipping any step is a violation.**

### Entry Sequence

```
1. Read docs/CODING_GUIDELINES.md  (this file — mandatory)
2. Read memory/PROJECT_RULES.md                 (project collaboration rules)
3. Read memory/ARCHITECTURE.md           (system architecture SSoT)
4. Read memory/HANDOFF.md                (previous session state)
5. Read memory/TASKS.md                  (current active tasks)
6. Begin execution
```

### Mandatory Directives

| Directive | Rule |
|:---|:---|
| **Read-Before-Write** | Before modifying any code, read the module and its docs. Never assume from memory. |
| **No Assumptions** | Never assume a file path exists. List the directory first. |
| **No Silent Changes** | Any logic change must update documentation simultaneously. No exceptions. |
| **Service Restart** | After any code change, confirm the relevant service has reloaded. |
| **Commit Discipline** | Every successfully verified change must be committed immediately using Conventional Commits. |
| **Environment Hygiene** | Never leave `.bak`, `.tmp`, test files, bare `print()` statements, or large commented-out blocks. |
| **Anti-Truncation Protocol** | Never summarise terminal commands, environment variables, or code blocks into descriptive prose. Preserve 100% of their content. |
| **SSoT Preservation** | Historical records in `DECISIONS.md` are never deleted. Abandoned decisions are marked `[ABANDONED]` with reasoning. |
| **Two-Tier Doc Boundary** | Never mix root `docs/` (infrastructure/deployment docs) with `open-claw-sandbox/docs/` (skill architecture docs). |

---

## 2. Code Quality Principles

### 2.1 Foundational Rules

- **DRY (Don't Repeat Yourself)**: Every piece of knowledge must have a single, authoritative representation. Duplicate logic → extract it.
- **YAGNI (You Aren't Gonna Need It)**: Only build what is needed right now. No speculative features.
- **KISS (Keep It Simple, Stupid)**: The simplest solution that works is the right one. Complexity is a liability.
- **Single Responsibility**: Each module/class/function should do exactly one thing and do it well.
- **Fail Fast**: Validate inputs at the boundary. Surface errors early with descriptive messages.

### 2.2 SOLID Principles

| Principle | Application |
|---|---|
| **S** — Single Responsibility | `AtomicWriter` writes files only. `PathBuilder` resolves paths only. |
| **O** — Open/Closed | `PipelineBase` is open for extension (new skill phases) but closed for modification. |
| **L** — Liskov Substitution | All phase classes must be substitutable for `PipelineBase`. |
| **I** — Interface Segregation | `OllamaClient` exposes only `generate()` and `chat()`. No mixed concerns. |
| **D** — Dependency Inversion | Skills depend on `core.orchestration.pipeline_base.PipelineBase`, not concrete implementations. |

---

## 3. Architecture & Design

### 3.1 Core Sub-Package Import Rules

> ⚠️ **The `core/` directory was refactored into domain sub-packages on 2026-05-01. All imports MUST use the full sub-package path.**

```python
# ✅ CORRECT
from core.utils.atomic_writer import AtomicWriter
from core.utils.bootstrap import ensure_core_path
from core.utils.log_manager import build_logger
from core.utils.path_builder import PathBuilder
from core.orchestration.pipeline_base import PipelineBase
from core.orchestration.task_queue import task_queue
from core.state.state_manager import StateManager
from core.state.resume_manager import ResumeManager
from core.ai.llm_client import OllamaClient
from core.services.inbox_daemon import SystemInboxDaemon
from core.services.security_manager import SecurityManager
from core.config.config_manager import ConfigManager

# ❌ WRONG (flat imports — broken after 2026-05-01 refactor)
from core.atomic_writer import AtomicWriter
from core.pipeline_base import PipelineBase
from core.state_manager import StateManager
```

### 3.2 Skill Bootstrap — Every Phase Script Must Start With

```python
from core.utils.bootstrap import ensure_core_path
ensure_core_path(__file__)
```

This idempotently adds the correct `open-claw-sandbox/` root to `sys.path`.

### 3.3 Skill Phase Conventions

- Phase scripts: `scripts/phases/p00_<name>.py`, `p01_<name>.py`, etc.
- Entry point: `scripts/run_all.py` (orchestrator — never contains business logic)
- All paths accessed via `self.dirs["key"]` from `config.yaml` — never hardcode.
- Outputs: always use `AtomicWriter` — never bare `open(..., "w")` for final output.
- State: call `self.state_manager.update_task(subject, filename, phase_key, "✅")` after each phase.

### 3.4 Data Flow Invariants

```
data/raw/<Subject>/       ← Only human-facing input point
        │
        ▼ (inbox_daemon routes)
data/<skill>/input/       ← Machine-only staging area (never write here manually)
        │
        ▼ (skill pipeline runs)
data/<skill>/output/      ← Intermediate phase outputs
        │
        ▼ (knowledge_compiler publishes)
data/wiki/<Subject>/      ← Obsidian Vault — final published knowledge
```

**Rules:**
- Skills must NOT write to another skill's `input/` or `output/` directories.
- Extraction skills (`audio_transcriber`, `doc_parser`) must NOT perform summarisation — delegate to `note_generator`.
- Annotation must NOT modify content — delegate to `smart_highlighter`.
- Source files (`.pdf`, `.m4a`) are **immutable** — read-only access only.

### 3.5 OOM Prevention — Task Queue Invariant

All skill invocations via `inbox_daemon` must be enqueued through `LocalTaskQueue`:

```python
from core.orchestration.task_queue import task_queue
task_queue.enqueue("skill-name Pipeline", cmd, cwd, filepath=filepath, skill=skill)
```

**Never spawn concurrent skill processes.** The Task Queue serialises all executions, preventing OOM from simultaneous LLM model loads.

---

## 4. Error Handling & Defensive Programming

### 4.1 Exception Strategy

```python
# ✅ Catch specific exceptions, log with context
try:
    result = process_file(path)
except FileNotFoundError as e:
    self.logger.error("❌ File not found: %s — %s", path, e)
    return False
except OSError as e:
    self.logger.error("❌ I/O error processing %s: %s", path, e, exc_info=True)
    raise

# ❌ Never do this
try:
    result = process_file(path)
except:
    pass
```

### 4.2 Error Classification

Use `core.utils.error_classifier.classify_exception()` for pipeline errors:

| Category | Behaviour |
|---|---|
| `RECOVERABLE` | Log warning, move to next file |
| `FATAL` | Log critical, stop the pipeline |
| `USER_ERROR` | Log error with actionable message to user |

### 4.3 Crash-Safe File Writes

**Always** use `AtomicWriter` for any important output:

```python
from core.utils.atomic_writer import AtomicWriter

# ✅ Atomic write (tempfile + os.replace — crash-safe)
AtomicWriter.write_text(output_path, content)
AtomicWriter.write_json(state_path, state_dict)

# ❌ Never use bare open() for important outputs
with open(output_path, "w") as f:
    f.write(content)
```

### 4.4 Input Validation at Boundaries

```python
# ✅ Validate at boundary, not inside deep logic
def process(self, filepath: str) -> bool:
    if not filepath.endswith((".m4a", ".mp3")):
        raise ValueError(f"Unsupported file type: {filepath}")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File does not exist: {filepath}")
    ...
```

---

## 5. Open Claw-Specific Invariants

### 5.1 LLM Configuration

- **Zero Temperature**: All production LLM calls must use `temperature: 0` (set in `config.yaml`). This prevents non-determinism, semantic drift, and hallucinations.
- **Explicit Timeout**: Always pass `timeout=600` (or higher for large docs). Never rely on default socket timeouts.
- **Model Unloading**: After heavy LLM inference, call `keep_alive=0` to force Ollama to unload the model from VRAM immediately.

```python
# ✅ Correct LLM call with all guards
response = self.client.generate(
    model=self.config["model"],
    prompt=prompt,
    temperature=0,
    timeout=600,
    keep_alive=0,
)
```

### 5.2 RAM Guard

`PipelineBase.check_system_health()` is called automatically at the start of each phase. It pauses execution if RAM drops below 15%. This is mandatory and must not be bypassed.

### 5.3 Anti-Hallucination Requirements (audio_transcriber)

The three-layer anti-hallucination defence must not be weakened:
1. `condition_on_previous_text=False` on MLX-Whisper
2. VAD silence trimming with safety valve (`silence_ratio < max_removal_ratio`)
3. N-gram/zlib repetition detection and chunk-level retry

### 5.4 PDF Security

All PDF inputs must pass through `SecurityManager` before any content is read:
- Path traversal check
- Filename allowlist validation
- File size cap check

### 5.5 Skill Name Convention (underscore only)

`skill_name` in `PipelineBase.__init__()` **must** use underscores and **must exactly match** the directory name under `skills/`. Using hyphens (e.g. `"smart-highlighter"`) will break `PathBuilder` config resolution.

```python
# ✅ Correct
super().__init__(skill_name="smart_highlighter")

# ❌ Wrong — hyphens cause PathBuilder to fail
super().__init__(skill_name="smart-highlighter")
```

### 5.6 Skill Entry Point Naming

All skill pipeline entry points **must** be named `run_all.py`. Custom names (`synthesize.py`, `highlight.py`, etc.) are prohibited. This ensures uniform routing by `RouterAgent` and consistent CLI conventions across all skills.

### 5.7 Reasoning Model `<think>` Tag Stripping

When using reasoning models (`phi4-mini-reasoning`, `deepseek-r1`, `qwen3` with thinking), the LLM output **must** be passed through `strip_think_tags()` before any further processing or file writes:

```python
from skills.note_generator.scripts.run_all import strip_think_tags

result = self.llm.generate(model=model, prompt=prompt, options=options)
result = strip_think_tags(result)  # ← mandatory for reasoning models
```

### 5.8 StateManager `raw_dir` Override

When a skill's input files originate from another skill's output directory (not from `data/<skill>/input/`), the `raw_dir` parameter **must** be explicitly passed to `StateManager` so the DAG dashboard shows correct file counts.

```python
# ✅ Correct — note_generator reads from proofreader output
proofread_dir = os.path.join(workspace_root, "data", "proofreader", "output", "00_doc_proofread")
self._state_manager = StateManager(self.base_dir, skill_name="note_generator", raw_dir=proofread_dir)

# ❌ Wrong — StateManager defaults to data/note_generator/input/*.m4a
self._state_manager = StateManager(self.base_dir, skill_name="note_generator")
```

---

## 6. Python Style & Formatting

### 6.1 Most Important Rule

> **Match the existing codebase style — even if you personally prefer something different. Consistency beats personal preference.**

### 6.2 Format Specifications

| Item | Rule |
|---|---|
| Indentation | 4 spaces (Python). Never use tabs. |
| Line width | Maximum 100 characters |
| Blank lines | Separate logical blocks with one blank line and a brief comment |
| Line endings | LF (Unix) only |
| Final newline | Every file must end with a newline |
| String quotes | Double quotes `"` for all strings; single quotes reserved for embedded strings |
| Large numbers | Use underscores for readability: `8_000`, `30_000` |

### 6.3 Toolchain (Enforced via `ops/check.sh`)

| Tool | Purpose | Config |
|---|---|---|
| `ruff check` | Linting (replaces flake8, isort, pyupgrade) | `pyproject.toml` |
| `ruff format` | Formatting (replaces black) | `pyproject.toml` |
| `mypy` | Static type checking | `pyproject.toml` |
| `shellcheck` | Shell script linting | CI |
| `pytest` | Unit and integration tests | `pyproject.toml` |

### 6.4 Imports

- Imports must be organised by `ruff` (stdlib → third-party → local)
- No wildcard imports: `from module import *` is forbidden
- All local imports must use the full `core.<subpackage>.<module>` path

### 6.5 `.editorconfig`

```ini
root = true

[*]
indent_style = space
indent_size = 2
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true

[*.py]
indent_size = 4

[*.md]
trim_trailing_whitespace = false
```

---

## 7. Type Annotations

### 7.1 Requirements

All **public** functions and methods must have complete type annotations:

```python
# ✅ Correct
def run(self, subject: str, filename: str, force: bool = False) -> bool: ...
def __init__(self) -> None: ...
def load_checkpoint(self) -> Optional[dict[str, str]]: ...

# ✅ Use built-in generics (Python 3.9+, required by this codebase)
def process(items: list[str]) -> dict[str, int]: ...

# ❌ Avoid legacy typing module for built-ins
from typing import List, Dict   # Only use for Optional, Union, Tuple, Any
def process(items: List[str]) -> Dict[str, int]: ...
```

### 7.2 Use of `Any`

`Any` is forbidden unless interfacing with an untyped third-party library, and must be documented:

```python
# ✅ Acceptable with explanation
from typing import Any
def parse_legacy_api(self, raw: Any) -> "ParsedResult":
    # raw comes from an untyped legacy SDK; type cannot be controlled
    ...

# ❌ Using Any to avoid thinking about types
def process(self, data: Any) -> Any: ...
```

### 7.3 Mypy Requirements

- No errors from `mypy core/` (enforced by `ops/check.sh`)
- `__init__` must return `-> None`
- All class attributes must have declared types or be initialised in `__init__`

---

## 8. Logging Standards

### 8.1 Always Use `build_logger` — Never `print()`

**No `print()` in skill phases.** All console I/O and debug output must use `log_manager`. This ensures that logs are structured, timestamped, and can be correctly captured by the JSON output formatter.

```python
# ✅ Correct
from core.utils.log_manager import build_logger
logger = build_logger("OpenClaw.MySkill", log_file=log_path, console=True)
logger.info("✅ Phase 1 complete: %s", filename)
logger.warning("⚠️ Fallback triggered for: %s", filepath)
logger.error("❌ Failed to process: %s", filename, exc_info=True)

# ❌ Never
print(f"Processing {filename}")
```

### 8.2 Log Level Guide

| Level | Emoji | When to use |
|---|---|---|
| `DEBUG` | `🔍` | Detailed internal state — dev only |
| `INFO` | `✅` | Successful milestone completions |
| `WARNING` | `⚠️` | Recoverable issue, processing continues |
| `ERROR` | `❌` | Task failed, continuing to next item |
| `CRITICAL` | `💥` | Fatal error, pipeline must stop |

### 8.3 Structured JSON Logging

Enable via environment variable for machine parsing:
```bash
OPENCLAW_LOG_JSON=1 python3 skills/audio_transcriber/scripts/run_all.py
```

---

## 9. Testing Standards

### 9.1 Location and Discovery

- Tests live in `open-claw-sandbox/tests/`
- Test files: `test_<module_name>.py`
- Run: `cd open-claw-sandbox && PYTHONPATH=. pytest tests/`

### 9.2 Mock Path Rules

When mocking with `@patch`, always use the **full sub-package path** where the symbol is **used** (not where it's defined):

```python
# ✅ Correct — patch where it is used
@patch("core.orchestration.task_queue.subprocess.run")
@patch("core.services.inbox_daemon.AtomicWriter.write_text")
@patch("core.state.state_manager.AtomicWriter.write_text")

# ❌ Wrong — old flat import paths (broken after 2026-05-01 refactor)
@patch("core.task_queue.subprocess.run")
@patch("core.inbox_daemon.AtomicWriter.write_text")
```

### 9.3 Test Coverage Targets

| Component | Minimum coverage |
|---|---|
| `core/utils/` | 90% |
| `core/orchestration/` | 85% |
| `core/state/` | 85% |
| `core/services/` | 70% |
| Skill phase scripts | Best-effort |

### 9.4 Test Types

- **Unit tests**: Test a single function/class in isolation. Mock all external calls.
- **Integration tests**: `tests/integration/` — test interactions between `core/` modules.
- **E2E tests**: `tests/e2e/` — reserved for full pipeline runs on test fixtures.

---

## 10. Git & Version Control

### 10.1 Branch Naming

```
main              → Stable, always deployable, protected
feature/<name>    → New feature (e.g., feature/telegram-weather-alert)
fix/<name>        → Bug fix (e.g., fix/api-null-response)
docs/<name>       → Documentation only
refactor/<name>   → Refactor without changing behaviour
chore/<name>      → Tooling, config, dependency updates
```

### 10.2 Conventional Commits

```
Format: <type>(<scope>): <description>

Types:
  feat      New feature
  fix       Bug fix
  docs      Documentation only
  refactor  Code refactor (no behaviour change)
  test      Add or modify tests
  chore     Tools, config, dependencies
  perf      Performance optimisation
  style     Formatting only (no logic change)

Examples:
  feat(audio_transcriber): add multi-clip majority-vote language detection
  fix(core): update all imports to new sub-package paths
  docs: translate all markdown files to English
  refactor(core): migrate flat core/ to domain sub-packages
  chore(deps): bump watchdog to 6.0.0
```

### 10.3 Commit Discipline

- **Commit after every successful verification**. Do not batch many unrelated changes.
- Commits must not contain debug code, temporary files, or credentials.
- Never force-push to `main`.

### 10.4 Required `.gitignore` Entries

```gitignore
# Runtime data (gitignored — generated on first run)
open-claw-sandbox/data/
open-claw-sandbox/models/
open-claw-sandbox/logs/

# Open WebUI runtime databases
infra/open-webui/vector_db/
infra/open-webui/webui.db*

# Python
__pycache__/
*.pyc
.venv/
*.egg-info/

# Environment
.env
.env.*
!.env.example

# Testing
.pytest_cache/
.coverage
htmlcov/

# Tools
.ruff_cache/
.mypy_cache/

# macOS
.DS_Store

# Logs
*.log
logs/
```

---

## 11. Security

### 11.1 PDF Safety (Mandatory)

All PDF inputs must pass through `SecurityManager` before reading:

```python
from core.services.security_manager import SecurityManager

sec = SecurityManager(workspace_root)
sec.validate_pdf(filepath)   # Raises SecurityViolationError on failure
```

This checks:
- Path traversal attempts
- Filename character allowlist
- File size limits

### 11.2 Secrets Management

- **Never** commit API keys, tokens, or passwords to git.
- Use environment variables for all secrets.
- `.env` files must be listed in `.gitignore`.
- Provide `.env.example` with all required variable names but no values.

### 11.3 Credential Detection

The global quality gate (`ops/check.sh`) runs a credential detection scan on every check. If triggered, investigate the file immediately.

---

## 12. Documentation Standards

### 12.1 Documentation Tier Structure

| Tier | Location | Owner | Contents |
|---|---|---|---|
| **Global** | `docs/` | Monorepo | `USER_MANUAL.md`, `CODING_GUIDELINES.md`, `STRUCTURE.md`, `INDEX.md` |
| **Global AI** | `memory/` | AI Agents | `ARCHITECTURE.md`, `DECISIONS.md`, `HANDOFF.md`, `PROJECT_RULES.md`, `TASKS.md` |
| **Skill** | `open-claw-sandbox/skills/<skill>/docs/` | Skill owner | `ARCHITECTURE.md`, `PROJECT_RULES.md`, `DECISIONS.md` |

### 12.2 Documentation Language

**All documentation must be written in English.** This enables the entire ecosystem (AI agents, LLMs, future contributors) to access and reason over the documentation without language barriers.

The only exception: AI output prompts may specify `Output MUST be in Traditional Chinese (zh-TW)` to preserve the end-user's preferred note language.

### 12.3 Anti-Truncation Protocol

> **⚠️ Absolute Rule: When updating any project documentation, AI agents must strictly adhere to the following:**

1. **Never summarise terminal commands.** All install, deploy, and start scripts (`pip install`, `chmod`, `launchctl setenv`) must be preserved in full Markdown code blocks. Never compress multiple commands into descriptive prose.
2. **Never assume the user knows the config.** All environment variables and `.env` file formats must be preserved 100%.
3. **Force restoration.** If a previous version has truncated details into a summary, you are obligated to restore the full information.

### 12.4 Decisions Log (ADR Format)

Every significant architectural decision must be logged in the appropriate `DECISIONS.md` using this format:

```markdown
## [YYYY-MM-DD] Decision Title

**Status:** Active | Abandoned (Reason: ...)
**Context:** Why was this decision needed?
**Decision:** What was decided?
**Consequences:** What are the trade-offs?
```

Decisions are **never deleted**. Abandoned decisions are marked `[ABANDONED]` with a reason.

---

## 13. Prohibited Patterns

| Pattern | Reason | Alternative |
|---|---|---|
| `print()` in production code | Non-structured, uncontrollable | `build_logger().info()` |
| `from core.X import Y` (flat) | Broken after 2026-05-01 refactor | `from core.<pkg>.X import Y` |
| `from module import *` | Namespace pollution | Explicit named imports |
| Bare `except:` | Swallows all errors silently | `except SpecificError as e:` |
| `time.sleep()` in pipelines | Blocks the task queue | Use event-based waiting |
| Hardcoded file paths | Breaks across environments | `self.dirs["key"]` from config |
| Writing to another skill's `input/` | Violates skill isolation | Use `inbox_daemon` routing |
| Concurrent skill launches | OOM risk | Always use `task_queue.enqueue()` |
| `temperature > 0` in production | Non-determinism, hallucinations | Always `temperature: 0` |
| Modifying source `.pdf` files | Violates immutability contract | Read-only access only |
| Bare `open(path, "w")` for final output | Not crash-safe | `AtomicWriter.write_text()` |
| `.bak`, `.tmp`, test files left in repo | Noise in version control | Delete before committing |
| Deleting records from `DECISIONS.md` | Historical context loss | Mark as `[ABANDONED]` |

---

## 14. Quick Reference

### Run the Quality Gate

```bash
# Root-level (all checks: sandbox + infra/pipelines + shell scripts + credential scan)
./ops/check.sh

# Sandbox-level (ruff lint + ruff format + mypy)
cd open-claw-sandbox
./ops/check.sh

# Run tests
cd open-claw-sandbox
PYTHONPATH=. pytest tests/ -q

# Auto-fix formatting and safe lint issues
cd open-claw-sandbox
ruff check --fix .
ruff format .
```

### Standard Skill Invocation

```bash
# All skills follow this pattern:
cd open-claw-sandbox
python3 skills/<skill-name>/scripts/run_all.py --process-all

# Common flags:
#   --force          Re-process even completed files
#   --resume         Continue from last checkpoint
#   --subject <name> Process only one subject folder
#   --from <N>       Start from phase N
#   --log-json       Structured JSON logging (for log aggregation)
```

### Core Import Cheat Sheet

```python
from core.utils.bootstrap import ensure_core_path; ensure_core_path(__file__)

from core.utils.atomic_writer import AtomicWriter
from core.utils.log_manager import build_logger
from core.utils.path_builder import PathBuilder
from core.orchestration.pipeline_base import PipelineBase
from core.orchestration.task_queue import task_queue
from core.state.state_manager import StateManager
from core.state.resume_manager import ResumeManager
from core.ai.llm_client import OllamaClient
from core.services.security_manager import SecurityManager
from core.config.config_manager import ConfigManager
```

---

## §15 AI-Native Documentation & Memory System

To maintain absolute context preservation across AI sessions, the repository implements a strict Document & Memory System Template. All human operators and AI agents MUST adhere to these rules:

### 15.1 System Structure
- **`identity/`**: Contains global AI personas (`AI_PROFILE.md`). Sandbox-specific identities remain in `open-claw-sandbox/`.
- **`memory/`**: The active AI workspace. Contains `PROJECT_RULES.md`, `DECISIONS.md`, `HANDOFF.md`, and `TASKS.md`.
- **`memory/sessions/`**: The immutable archive of past AI execution logs and implementation plans.
- **`docs/`**: Human-readable global SSoT documentation (e.g., `ARCHITECTURE.md`, `DEVELOPMENT_MANUAL.md`).

### 15.2 The "Append vs. Rewrite" Rules Matrix
To prevent context loss while maintaining a clean workspace, files are strictly categorized into Append-Only (Immutable) and Rewriteable (Mutable) states.

#### Append-Only (Never Delete)
*   **`memory/HISTORY.md`**: Master session index.
*   **`memory/DECISIONS.md`**: If a previous decision is overturned, mark it as `[ABANDONED] (Reason: ...)` and append the new ADR below it.
*   **`CHANGELOG.md`**: Standard version tracking.
*   **`memory/sessions/*.md`**: The immutable archive of past execution logs.

#### Rewriteable (Keep Current)
*   **`memory/HANDOFF.md`**: Completely overwrite at the end of each session to reflect the exact current state.
*   **`memory/TASKS.md`**: Update checkboxes. Completed tasks can be moved to the bottom or archived.
*   **`docs/ARCHITECTURE.md` & `docs/STRUCTURE.md`**: Overwrite to perfectly match the current reality of the codebase.
*   **`memory/PROJECT_RULES.md` & `identity/AI_PROFILE.md`**: Update and refine whenever workflows or hardware constraints change.

### 15.3 Session Handoff & Archival
- **End of Session**: Before completing a major milestone, AI agents MUST update `memory/HANDOFF.md` to record the current state and provide the next starting point.
- **Archival Protocol**: After every significant execution session, the `implementation_plan.md` and `walkthrough.md` generated by the AI MUST be archived into `memory/sessions/YYYY-MM-DD_<topic>.md` and linked in `memory/HISTORY.md`. This ensures `CHANGELOG.md` and `DECISIONS.md` remain clean while preserving 100% of the granular implementation history.

---

## Version History

| Version | Date | Changes |
|---|---|---|
| v4.1.0 | 2026-05-05 | Appended §15 AI-Native Documentation & Memory System rules and archival protocols |
| v4.0.0 | 2026-05-01 | Global English translation; added core/ sub-package import rules; added Task Queue OOM invariant; updated test mock path rules; added Mypy strict guidelines |
| v3.0.0 | 2026-04-22 | Added SSoT doc strategy; Anti-Truncation Protocol; dual-tier doc boundary rule |
| v2.0.0 | 2026-04-19 | Added OOM prevention via LocalTaskQueue; RAM Guard invariant; Zero Temperature mandate |
| v1.0.0 | 2026-03-30 | Initial version |
