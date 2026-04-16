# Open Claw — Coding Guidelines & Architecture Reference

> Version: 3.1 | Last Updated: 2026-04-16
> This document is the **single source of truth** for all Open Claw development.
> Every new skill, phase script, and core module **must** conform to these standards.

---

## Table of Contents

0. [AI Agent Workflow & Directives](#0-ai-agent-workflow--directives)
1. [Core Design Principles](#1-core-design-principles)
2. [Directory Structure](#2-directory-structure)
3. [Skill Development Standards](#3-skill-development-standards)
4. [Core Module Usage](#4-core-module-usage)
5. [Naming Conventions](#5-naming-conventions)
6. [Configuration Schema (config.yaml)](#6-configuration-schema-configyaml)
7. [Error Handling](#7-error-handling)
8. [CLI Design Standards](#8-cli-design-standards)
9. [Documentation Standards](#9-documentation-standards)
10. [Prohibited Patterns](#10-prohibited-patterns)
11. [Python Code Style](#11-python-code-style)
12. [Type Annotations](#12-type-annotations)
13. [Docstrings](#13-docstrings)
14. [Enforcement & Tooling](#14-enforcement--tooling)

---

## 0. AI Agent Workflow & Directives

**ATTENTION ALL AI AGENTS:** This document (`CODING_GUIDELINES.md`) is your primary operational directive. You MUST read this file at the beginning of *any* session interacting with this workspace.

### Mandatory Workflow for Every Action
1. **Read Guidelines First**: Acknowledge and adhere strictly to the rules defined in this document (e.g. DRY principle, config-driven paths, core module boundaries).
2. **Execute Cleanly**: Keep code elegant, symmetrical, and perfectly optimized. Encapsulate all repeated behaviors into `core/`.
3. **Synchronize Documentation**:
   - If you add or remove features, classes, or behaviors, you **MUST** update all corresponding `.md` files in `docs/` and the relevant skill's `docs/` folder (e.g., `ARCHITECTURE.md`, `CLAUDE.md`, `STRUCTURE.md`).
4. **Git Version Control**:
   - Commit all successful, verified changes to the local Git repository immediately with a clear, descriptive commit message.
   - If an upstream remote exists, push to GitHub/remote after committing.
5. **Enforce Hygiene**: Never leave stale files, duplicated functions, or temporary backups (`.bak`, `.tmp`) lying around.

---

## 1. Core Design Principles

| Principle | Description |
|:---|:---|
| **Zero Hardcoded Paths** | All directory paths must be resolved through `config.yaml` → `PathBuilder` → `self.dirs[key]` |
| **Single Source of Truth** | Every piece of functionality has exactly one implementation, located in `core/` |
| **OOP + Encapsulation** | All phase scripts extend `PipelineBase`; all utilities are encapsulated as classes |
| **Atomic Writes** | All persistent file writes must use `AtomicWriter` to prevent corruption on failure |
| **Backward Compatibility** | Changes to `core/` modules must not break existing skill scripts |
| **Interruptible** | All long-running operations must support graceful shutdown on `Ctrl+C` (once) and forced exit (twice) |
| **Config-Driven Paths** | The `PathBuilder` reads `paths:` from `config.yaml`; no `if skill_name ==` branching anywhere |

---

## 2. Directory Structure

```
open-claw-workspace/
├── core/                          # Shared framework used by all skills
│   ├── __init__.py                # Unified public API exports
│   ├── bootstrap.py               # One-line sys.path fix (replaces Boundary-Safe Init)
│   ├── pipeline_base.py           # OOP base class for all Phase scripts
│   ├── state_manager.py           # Pipeline state tracking + checklist.md rendering
│   ├── path_builder.py            # Config-driven path resolution
│   ├── config_manager.py          # YAML/JSON configuration reader
│   ├── llm_client.py              # OllamaClient (retries, timeouts, model unloading)
│   ├── atomic_writer.py           # Atomic write (write-then-rename)
│   ├── security_manager.py        # Input security scanning
│   ├── resume_manager.py          # Checkpoint / resume management
│   ├── diff_engine.py             # DiffEngine + AuditEngine (skill-agnostic)
│   ├── glossary_manager.py        # Cross-skill terminology synchronisation
│   ├── text_utils.py              # Text chunking utilities
│   ├── error_classifier.py        # Error classification
│   ├── log_manager.py             # Logger factory
│   ├── cli.py                     # Shared CLI argument parser builder
│   ├── cli_config_wizard.py       # Interactive model profile switcher
│   ├── inbox_daemon.py            # Global inbox file watcher daemon
│   ├── data_layout.py             # Data directory layout management
│   ├── config_validation.py       # Configuration validation
│   └── web_ui/                    # Flask web dashboard
│       ├── app.py
│       └── templates/index.html
│
├── skills/
│   ├── SKILL.md                   # Skill registry + new-skill creation guide
│   ├── voice-memo/
│   │   ├── SKILL.md               # Quick-start reference
│   │   ├── config/config.yaml     # Paths, models, thresholds
│   │   ├── docs/
│   │   │   ├── ARCHITECTURE.md    # Technical architecture
│   │   │   ├── DECISIONS.md       # Technical decision log
│   │   │   └── CLAUDE.md          # AI collaboration context
│   │   └── scripts/
│   │       ├── run_all.py         # Orchestrator
│   │       ├── phases/p0N_*.py    # Phase scripts
│   │       └── utils/subject_manager.py  # Voice-memo-specific CLI helpers
│   └── pdf-knowledge/
│       ├── SKILL.md
│       ├── config/config.yaml
│       ├── docs/
│       │   ├── ARCHITECTURE.md
│       │   ├── DECISIONS.md
│       │   └── CLAUDE.md
│       └── scripts/
│           ├── run_all.py
│           └── phases/p0Na_*.py   # Phase scripts
│
├── data/                          # Runtime data — excluded from version control
│   ├── voice-memo/
│   │   ├── input/raw_data/<subject>/*.m4a
│   │   ├── output/01_transcript/ … 05_notion_synthesis/
│   │   ├── state/.pipeline_state.json
│   │   └── logs/system.log
│   └── pdf-knowledge/
│       ├── input/01_Inbox/<subject>/*.pdf
│       ├── output/02_Processed/ … 05_Final_Knowledge/
│       ├── state/.pipeline_state.json
│       └── logs/system.log
│
├── docs/CODING_GUIDELINES.md      # This document
├── ops/                           # One-off operational scripts (delete after use)
└── models/                        # Locally downloaded model files
```

---

## 3. Skill Development Standards

### 3.1 Standard Phase Script Structure

```python
# -*- coding: utf-8 -*-
"""
Phase N — Description (skills/<skill>/scripts/phases/pNN_name.py)
"""
# ── 1. Bootstrap (replaces the old Boundary-Safe Init block) ─────────────────
import os, sys
from core.bootstrap import ensure_core_path as _bootstrap
_bootstrap(__file__)
_workspace_root = os.environ.get(
    "WORKSPACE_DIR",
    os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../.."))
)

# ── 2. Standard imports ───────────────────────────────────────────────────────
from core import PipelineBase, AtomicWriter

# ── 3. Phase class ────────────────────────────────────────────────────────────
class PhaseNMyProcess(PipelineBase):
    def __init__(self):
        super().__init__(
            phase_key="pN",
            phase_name="My Processing Step",
            skill_name="my-skill"   # Must match the skills/ directory name exactly
        )
        # self.dirs["pN"]    → resolved from config.yaml paths.phases.pN
        # self.llm           → OllamaClient, auto-configured
        # self.state_manager → StateManager, auto-configured

    def run(self, subject: str, filename: str) -> bool:
        input_path  = os.path.join(self.dirs["pN-1"], subject, ...)
        output_path = os.path.join(self.dirs["pN"],   subject, ...)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # ... business logic ...

        AtomicWriter.write_text(output_path, result)  # Always use AtomicWriter
        self.info(f"✅ Phase N complete: {output_path}")
        return True

# ── 4. Optional standalone CLI entry point ───────────────────────────────────
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--subject", required=True)
    p.add_argument("--file",    required=True)
    args = p.parse_args()
    PhaseNMyProcess().run(args.subject, args.file)
```

### 3.2 Orchestrator (`run_all.py`) Standards

```python
class MyOrchestrator(PipelineBase):
    def startup_check(self) -> bool:
        # ... preflight checks (model availability, disk space, etc.) ...
        self.state_manager.sync_physical_files()  # Required: initialises checklist.md
        return True

    def process_one(self, subject: str, filename: str):
        try:
            PhaseNMyProcess().run(subject, filename)
            self.state_manager.update_task(subject, filename, "pN", "✅")  # Required
        except Exception as e:
            self.state_manager.update_task(subject, filename, "pN", "❌", note_tag=str(e))
            raise
```

### 3.3 Creating a New Skill

1. **Create directories** — `mkdir -p skills/my-skill/{config,docs,scripts/phases}`
2. **Write `config/config.yaml`** — include `paths:`, `runtime.ollama`, and `hardware` sections
3. **Write phase scripts** — inherit `PipelineBase`, use `ensure_core_path`
4. **Write `run_all.py`** — call `state_manager.sync_physical_files()` at startup
5. **Register in `core/inbox_daemon.py`** — add the new inbox path to the watcher config
6. **Write docs** — `SKILL.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `CLAUDE.md`

---

## 4. Core Module Usage

### 4.1 PathBuilder — Path Resolution

```python
# ✅ Correct: access paths through self.dirs
output = os.path.join(self.dirs["p1"], subject, f"{stem}.md")

# ❌ Wrong: any form of hardcoded path string
output = "/Users/xxx/data/voice-memo/output/01_transcript/..."
```

### 4.2 AtomicWriter — Safe File Writes

```python
# ✅ Correct: atomic write prevents corruption on interruption
from core import AtomicWriter
AtomicWriter.write_text(path, content)
AtomicWriter.write_json(path, data)

# ❌ Wrong: direct open() write — leaves corrupt files if interrupted
with open(path, "w") as f:
    f.write(content)
```

### 4.3 StateManager — Progress Tracking

| Method | When to Call |
|:---|:---|
| `state_manager.sync_physical_files()` | At orchestrator startup — scans inbox, creates initial state |
| `state_manager.update_task(subject, file, key, "✅")` | Immediately after each phase completes successfully |
| `state_manager.update_task(subject, file, key, "❌", note_tag=...)` | When a phase fails |
| `state_manager.cascade_invalidate(subject, file, key)` | When a phase output is manually edited |
| `state_manager.save_checkpoint(subject, file, key)` | Before a graceful shutdown |

### 4.4 DiffEngine — File Comparison

```python
# ✅ Correct: use core.DiffEngine (skill-agnostic, any two text files)
from core.diff_engine import DiffEngine
engine = DiffEngine()
result = engine.diff_files(path_a, path_b, label_a="Phase 1", label_b="Phase 2")

# ❌ Wrong: importing the old voice-memo diff_tool.py (deleted)
```

### 4.5 bootstrap — sys.path Initialisation

```python
# ✅ Correct: single line at the top of every phase script
from core.bootstrap import ensure_core_path
ensure_core_path(__file__)

# ❌ Wrong: the old 10-line "Boundary-Safe Initialization" block
#   (removed from all scripts — do not reintroduce)
_script_dir = os.path.dirname(os.path.abspath(__file__))
_skill_root = os.path.dirname(_script_dir)
...
sys.path.insert(0, _openclawed_root)
```

### 4.6 OllamaClient — LLM Calls

```python
# ✅ Correct: use self.llm (auto-configured from config.yaml)
response = self.llm.generate(model=self.model, prompt=prompt, logger=self)
self.llm.unload_model(self.model, logger=self)  # Free VRAM after heavy inference

# ❌ Wrong: raw requests.post to Ollama
import requests
requests.post("http://localhost:11434/api/generate", json={...})
```

---

## 5. Naming Conventions

### 5.1 Phase Script File Names

```
p<number><optional_letter>_<descriptive_name>.py

Examples:
  p01_transcribe.py        ← voice-memo (single-number, no letter suffix)
  p01a_diagnostic.py       ← pdf-knowledge (letter suffix distinguishes sub-phases)
  p02b_synthesis.py
```

### 5.2 Classes

```python
class Phase2Proofread(PipelineBase): ...    # ✅ Phase + number + function name
class QueueManager(PipelineBase):   ...     # ✅ Semantically clear
class DiffEngine:                   ...     # ✅ Tool class — clear noun
class p2_run:                       ...     # ❌ Unclear, wrong casing
```

### 5.3 Methods

- Public methods: `snake_case` — `run()`, `run_vision()`, `generate_diff()`
- Private helpers: `_snake_case` — `_build_html()`, `_resolve_path()`
- Properties: `snake_case` — `phase_dirs`, `canonical_dirs`

### 5.4 `config.yaml` `paths.phases` Keys

Keys become `self.dirs[key]` in phase scripts. Use:
- Phase keys for sequential pipelines: `p1`, `p2`, `p3`
- Semantic names for non-sequential workflows: `inbox`, `processed`, `final`, `error`

### 5.5 Variables

```python
# ✅ Descriptive, unambiguous
output_path = os.path.join(self.dirs["p2"], subject, f"{stem}.md")
retention_ratio = len(final_content) / max(1, len(raw_text))

# ❌ Single letters or abbreviations
op = os.path.join(...)
rr = len(fc) / len(rt)
```

---

## 6. Configuration Schema (config.yaml)

### 6.1 Required Sections

```yaml
# ── Paths (required) ───────────────────────────────────────────────────────
# All values are relative to data/<skill-name>/
paths:
  input:  "input/..."         # Required: canonical input root
  output: "output"            # Required: canonical output root
  state:  "state"             # Required: state JSON + checklist.md
  logs:   "logs"              # Required: log files
  phases:                     # Required: at least one phase key
    phase1: "output/01_result"
    phase2: "output/02_final"

# ── Runtime (required) ─────────────────────────────────────────────────────
runtime:
  ollama:
    api_url: "http://localhost:11434/api/generate"
    timeout_seconds: 600
    retries: 3
    backoff_seconds: 5.0

# ── Hardware (recommended) ─────────────────────────────────────────────────
hardware:
  ram:
    warning_mb: 800
    critical_mb: 400
  temperature:
    warning_celsius: 85
    critical_celsius: 95
  battery:
    min_percent: 15
  disk:
    min_free_mb: 500
```

### 6.2 Model Profile Pattern

`active_profile` is the only field that changes to switch models. Use `cli_config_wizard.py` to switch interactively — never edit profiles by hand during a run.

```yaml
phaseN:
  active_profile: default     # Change this value to switch models
  profiles:
    default:
      model: gemma3:12b
      options:
        num_ctx: 16384
        temperature: 0.1
    fast_draft:
      model: gemma3:4b
      options:
        num_ctx: 8192
        temperature: 0.3
```

Switch command: `python3 core/cli_config_wizard.py --skill <skill-name>`

---

## 7. Error Handling

```python
# ✅ Correct: specific error context, caller decides recovery strategy
try:
    result = self.llm.generate(model=model, prompt=prompt)
except Exception as e:
    self.error(f"❌ [Phase2] LLM generation failed ({subject}/{filename}): {e}")
    return False   # Let the orchestrator decide whether to continue

# ❌ Wrong: silently swallowing exceptions
try:
    ...
except:
    pass

# ❌ Wrong: catching Exception and re-raising bare
try:
    ...
except Exception:
    raise
```

### Error Severity Guidelines

| Method / Action | When to Use |
|:---|:---|
| `self.info(...)` | Normal progress — phase started, file written |
| `self.warning(...)` | Recoverable issue — file skipped, retrying |
| `self.error(...)` | Phase failed — continue with next file |
| `os._exit(1)` | Hardware emergency only — RAM exhausted, disk full |
| `raise RuntimeError(...)` | Unrecoverable state — let orchestrator handle |

---

## 8. CLI Design Standards

### 8.1 Standard Flags for All Orchestrators

```python
parser = argparse.ArgumentParser(description="<Skill Name> Pipeline Orchestrator")
parser.add_argument("--subject",     metavar="NAME",
                    help="Process only the specified subject folder")
parser.add_argument("--force",       action="store_true",
                    help="Reprocess and overwrite already-completed phases")
parser.add_argument("--resume",      action="store_true",
                    help="Resume from the last saved checkpoint")
parser.add_argument("--interactive", action="store_true",
                    help="Pause at key checkpoints for manual review")
```

### 8.2 Console Output Style

Use consistent emoji prefixes for all terminal output:

| Emoji | Meaning |
|:---:|:---|
| `✅` | Success — phase or file completed |
| `⚠️` | Warning — recoverable issue, processing continues |
| `❌` | Error — file or phase failed, continuing with next |
| `🔄` | In progress — currently running |
| `⏸️` | Paused — waiting for user input |
| `🚨` | Critical — graceful shutdown initiated |
| `💥` | Fatal — forced exit due to hardware emergency |

### 8.3 Interrupt Behaviour

All orchestrators must handle `SIGINT`:

```python
import signal

def _handle_interrupt(signum, frame):
    if self.stop_requested:
        self.error("💥 Second interrupt — forced exit.")
        os._exit(1)
    self.warning("🚨 Interrupt received — will stop after current file. (Press again to force exit.)")
    self.stop_requested = True

signal.signal(signal.SIGINT, _handle_interrupt)
```

---

## 9. Documentation Standards

Every skill **must** include the following, and **only** the following:

| Document | Location | Purpose |
|:---|:---|:---|
| `SKILL.md` | `skills/<skill>/` | Quick-start: phases table, common commands, config pointers |
| `ARCHITECTURE.md` | `skills/<skill>/docs/` | Directory layout, class hierarchy, data-flow diagram, core dependencies |
| `DECISIONS.md` | `skills/<skill>/docs/` | Technical decisions and trade-offs (date-stamped) |
| `CLAUDE.md` | `skills/<skill>/docs/` | AI collaboration context — what the AI assistant needs to know |

**Do not** create `TASKS.md`, `PROGRESS.md`, `HANDOFF.md`, or `WALKTHROUGH.md`.
These are ephemeral session documents — delete them when the work is done.

---

## 10. Prohibited Patterns

| Prohibited | Required Alternative |
|:---|:---|
| Hardcoded path strings anywhere in code | `self.dirs[key]` via `PathBuilder` + `config.yaml` |
| The 10-line "Boundary-Safe Initialization" `sys.path` block | `from core.bootstrap import ensure_core_path; ensure_core_path(__file__)` |
| One skill importing from another skill's directory | Extract shared logic to `core/` |
| One-off fix scripts inside `skills/` | Place in `ops/`; delete after use |
| `open(path, "w")` for pipeline output files | `AtomicWriter.write_text(path, content)` |
| Copying `diff_tool.py` or `audit_tool.py` into a skill | `from core.diff_engine import DiffEngine, AuditEngine` |
| `StateManager()` without `skill_name` | `StateManager(base_dir, skill_name="my-skill")` |
| Global path constants at module level | Resolve at runtime via `self.dirs`, `self.base_dir`, `self.config_manager` |
| LLM calls via raw `requests.post` | `self.llm.generate(model=..., prompt=..., logger=self)` |
| Catching exceptions silently with bare `except: pass` | Log with `self.error(...)` and return a failure indicator |

---

## 11. Python Code Style

Open Claw follows **PEP 8** with project-specific constraints listed below.
All formatting is enforced by **Ruff** (see [Section 14](#14-enforcement--tooling)).

### 11.1 Formatting

| Rule | Value | Rationale |
|:---|:---:|:---|
| Indent | 4 spaces | PEP 8 standard; never tabs |
| Max line length | 100 characters | Readable on split-screen without wrapping |
| String quotes | Double `"` | Consistent; single quotes reserved for inner strings |
| Trailing commas | Required on multi-line | Clean diffs — adding an item never changes the last line |
| Blank lines between methods | 1 | 2 between top-level classes/functions |
| Encoding declaration | `# -*- coding: utf-8 -*-` | First line of every `.py` file |

```python
# ✅ Correct formatting
class Phase2Proofread(PipelineBase):

    def __init__(self) -> None:
        super().__init__(
            phase_key="p2",
            phase_name="Proofreading",
            skill_name="voice-memo",
        )                             # ← trailing comma on last arg

    def run(
        self,
        subject: str,
        filename: str,
        force: bool = False,
    ) -> bool:                        # ← return type always annotated
        ...


# ❌ Wrong
class Phase2Proofread(PipelineBase):
  def __init__(self):               # 2-space indent, no return type
    super().__init__('p2','Proofreading','voice-memo') # jammed together
```

### 11.2 Import Ordering

Imports are grouped in exactly this order, separated by a blank line each:

```python
# Group 1 — stdlib
import os
import sys
import json
import signal
import threading
from datetime import datetime
from functools import cached_property
from typing import Dict, List, Optional, Tuple

# Group 2 — third-party
import psutil
import yaml

# Group 3 — internal core (after bootstrap)
from core.bootstrap import ensure_core_path as _bootstrap
_bootstrap(__file__)

from core import PipelineBase, AtomicWriter
from core.diff_engine import DiffEngine
```

Rules:
- **Never** use wildcard imports: `from module import *`
- **Never** import inside a function body unless avoiding a circular dependency
- **Always** import `bootstrap` before any `core` import

### 11.3 Class Structure Order

Within every class, sections appear in this fixed order:

```python
class MyClass:
    # 1. Class-level constants
    MAX_RETRIES = 3
    TIMEOUT_MS  = 30_000

    # 2. __init__
    def __init__(self, ...) -> None: ...

    # 3. Class methods and static methods
    @classmethod
    def from_config(cls, path: str) -> "MyClass": ...

    @staticmethod
    def _validate(value: str) -> bool: ...

    # 4. Public properties
    @property
    def name(self) -> str: ...

    # 5. Public methods (alphabetical within same logical group)
    def diff_files(self, ...) -> DiffResult: ...
    def write_html(self, ...) -> str: ...

    # 6. Private methods (prefixed with _)
    def _build_html(self, ...) -> str: ...
    def _resolve(self, rel: str) -> str: ...

    # 7. __repr__ and __str__ last
    def __repr__(self) -> str: ...
```

### 11.4 Numeric Literals

Use underscores for readability in large numbers:

```python
# ✅
MAX_CHUNK_CHARS = 8_000
MAX_RAM_MB      = 2_560
TIMEOUT_MS      = 30_000

# ❌
MAX_CHUNK_CHARS = 8000
```

### 11.5 f-Strings

Always prefer f-strings over `.format()` or `%` formatting:

```python
# ✅
self.info(f"✅ Phase 2 complete: {os.path.basename(output_path)} ({len(result):,} chars)")

# ❌
self.info("✅ Phase 2 complete: %s (%d chars)" % (os.path.basename(output_path), len(result)))
self.info("✅ Phase 2 complete: {} ({} chars)".format(os.path.basename(output_path), len(result)))
```

### 11.6 Collections and Data Structures

Use dataclasses for structured data — never plain dicts for function returns:

```python
# ✅ Correct: typed, self-documenting
from dataclasses import dataclass, field
from typing import List

@dataclass
class DiffResult:
    file_a:    str
    file_b:    str
    additions: int = 0
    deletions: int = 0
    success:   bool = True
    error:     str = ""

def diff_files(self, path_a: str, path_b: str) -> DiffResult:
    result = DiffResult(file_a=path_a, file_b=path_b)
    ...
    return result

# ❌ Wrong: opaque, type-unsafe
def diff_files(self, path_a, path_b):
    return {"file_a": path_a, "additions": 0, "ok": True}
```

### 11.7 Constants and Magic Values

Every "magic" number or string must be a named constant at class or module level:

```python
# ✅
MIN_RETENTION_RATIO = 0.30   # content-loss guard threshold
DEBOUNCE_SECONDS    = 3.0    # wait for file copy to complete

if retention_ratio < MIN_RETENTION_RATIO:
    ...

# ❌
if retention_ratio < 0.30:
    ...
```

---

## 12. Type Annotations

All public functions and methods **must** have complete type annotations.
Private helpers should be annotated where the types are non-obvious.

### 12.1 Required Patterns

```python
# All __init__ methods return None
def __init__(self) -> None: ...

# All public methods are fully annotated
def run(self, subject: str, filename: str, force: bool = False) -> bool: ...

# Use Optional for nullable parameters (prefer X | None in Python 3.10+, Optional[X] for 3.9)
def load_checkpoint(self) -> Optional[Dict[str, str]]: ...

# Use List, Dict, Tuple from typing for Python 3.9 (repo target)
from typing import Dict, List, Optional, Tuple

def aggregate_directory(
    self,
    directory: str,
    log_marker: str,
    phase_tag: str,
    min_count: int = 1,
) -> Dict[Tuple[str, str], AuditEntry]: ...
```

### 12.2 Forward References

Use string literals for forward references (class not yet defined):

```python
@classmethod
def from_config(cls, path: str) -> "PathBuilder": ...
```

### 12.3 Generics and Complex Types

Define type aliases for complex repeated signatures:

```python
# ✅ Alias at module level
from typing import Dict, List, Tuple
PhaseMap   = Dict[str, str]                          # {"p1": "/abs/path"}
AuditIndex = Dict[Tuple[str, str], "AuditEntry"]    # {(before, after): entry}

def phase_dirs(self) -> PhaseMap: ...
def aggregate(self) -> AuditIndex: ...
```

### 12.4 Do Not Use

```python
# ❌ Bare Any — loses all type safety
from typing import Any
def process(self, data: Any) -> Any: ...

# ❌ Missing return type on public method
def run(self, subject: str, filename: str): ...

# ❌ Using built-in dict/list without type params (Python 3.9 style — use typing module)
def get_dirs(self) -> dict: ...   # Should be Dict[str, str]
```

---

## 13. Docstrings

All public classes and public methods must have docstrings.
Use **Google style** (not NumPy or reStructuredText).

### 13.1 Module Docstring

```python
# -*- coding: utf-8 -*-
"""
core/diff_engine.py — Open Claw Universal Diff & Audit Engine
=============================================================
Short one-line summary.

Longer description of purpose, design decisions, and key behaviours.
Mention what this module replaces if it supersedes an older file.

Typical usage::

    engine = DiffEngine()
    result = engine.diff_files(path_a, path_b, label_a="P1", label_b="P2")
    engine.write_html(result, "/output/diff.html", auto_open=True)
"""
```

### 13.2 Class Docstring

```python
class DiffEngine:
    """
    Skill-agnostic side-by-side HTML diff generator.

    Compares any two text files and produces a DiffResult containing
    the HTML report and change statistics. Zero coupling to any skill —
    callers pass raw file paths.

    Attributes:
        context_lines: Number of unchanged lines shown around each change.
        wrap_columns:  Column width for line wrapping in the HTML report.

    Example::

        engine = DiffEngine(context_lines=5)
        result = engine.diff_files("before.md", "after.md")
        if result.success:
            engine.write_html(result, "diff_report.html", auto_open=True)
    """
```

### 13.3 Method Docstring

```python
def diff_files(
    self,
    path_a: str,
    path_b: str,
    label_a: str = "",
    label_b: str = "",
    strip_log_marker: Optional[str] = None,
) -> DiffResult:
    """
    Compare two text files and return a structured DiffResult.

    The comparison is line-based. If strip_log_marker is provided,
    everything from that string onward in path_b is excluded before
    comparison (useful for stripping audit-log footers).

    Args:
        path_a: Absolute path to the "before" file.
        path_b: Absolute path to the "after" file.
        label_a: Human-readable label shown in the HTML report header.
        label_b: Human-readable label shown in the HTML report header.
        strip_log_marker: If set, truncate path_b content at this marker
            before comparing (e.g. "## Changelog").

    Returns:
        A DiffResult with html_report, additions, deletions, and char_delta.
        On error, DiffResult.success is False and DiffResult.error is set.

    Raises:
        Does not raise. All errors are captured in DiffResult.error.
    """
```

### 13.4 What NOT to Write

```python
# ❌ Restating the obvious — useless docstring
def get_file_hash(self, filepath: str) -> str:
    """Get the file hash."""
    ...

# ❌ No docstring on a public, non-trivial method
def ensure_directories(self) -> None:
    for path in [...]:
        os.makedirs(path, exist_ok=True)
```

### 13.5 Inline Comments

Use inline comments sparingly — only for non-obvious logic:

```python
# ✅ Comments explain WHY, not WHAT
sha256 = hashlib.sha256()
with open(filepath, "rb") as f:
    for block in iter(lambda: f.read(4096), b""):   # 4 KB chunks — optimal for spinning disks
        sha256.update(block)

# ❌ Stating the obvious
result = []                # Create an empty list
for item in items:         # Loop over items
    result.append(item)    # Append item to result
```

---

## 14. Enforcement & Tooling

### 14.1 Linter and Formatter — Ruff

All Python code must pass `ruff check` and `ruff format` with zero warnings.

**Install:**
```bash
pip install ruff
```

**Project configuration (add to `pyproject.toml` or `ruff.toml`):**
```toml
[tool.ruff]
target-version = "py39"
line-length = 100

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes (undefined names, unused imports)
    "I",    # isort (import ordering)
    "N",    # pep8-naming
    "UP",   # pyupgrade (modern Python syntax)
    "B",    # flake8-bugbear (common bugs)
    "C4",   # flake8-comprehensions (cleaner list/dict comps)
    "SIM",  # flake8-simplify
    "RUF",  # ruff-specific rules
]
ignore = [
    "E501",   # line length — handled by ruff format, not ruff check
]

[tool.ruff.lint.isort]
known-first-party = ["core"]
force-sort-within-sections = true
```

**Run:**
```bash
# Check all Python files
ruff check open-claw-workspace/

# Auto-fix safe issues
ruff check --fix open-claw-workspace/

# Format (Black-compatible)
ruff format open-claw-workspace/
```

### 14.2 Static Type Checker — Mypy

Run mypy on `core/` to catch type errors before runtime.

**Install:**
```bash
pip install mypy
```

**Configuration (add to `pyproject.toml`):**
```toml
[tool.mypy]
python_version = "3.9"
strict = false                  # Not strict globally — too noisy for legacy code
disallow_untyped_defs = true    # All public methods must have type annotations
warn_return_any = true
warn_unused_ignores = true
ignore_missing_imports = true   # Third-party stubs may be missing
```

**Run:**
```bash
mypy open-claw-workspace/core/
```

### 14.3 Pre-commit Hooks

Set up pre-commit to automatically enforce style **before every commit**.

**Install:**
```bash
pip install pre-commit
```

**`.pre-commit-config.yaml` (place in `open-claw-workspace/`):**
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-merge-conflict
      - id: debug-statements       # Catches leftover breakpoint() / pdb calls
```

**Enable:**
```bash
cd open-claw-workspace
pre-commit install     # Runs on every git commit automatically
pre-commit run --all-files   # Run on all files right now
```

### 14.4 Manual Code Review Checklist

Every pull request or significant change must be self-reviewed against this checklist before merging:

#### Architecture
- [ ] New code in `skills/` does not import from another skill's directory
- [ ] Shared logic is placed in `core/`, not duplicated across skills
- [ ] `core/` changes are backward-compatible with all existing skill scripts
- [ ] New skill directories follow the standard layout in `skills/SKILL.md`

#### Code Quality
- [ ] `ruff check` passes with zero warnings
- [ ] `ruff format` produces no changes (already formatted)
- [ ] All public methods have complete type annotations
- [ ] All public classes and non-trivial methods have Google-style docstrings
- [ ] All magic numbers and strings are named constants
- [ ] No `except: pass` or silent exception swallowing

#### Open Claw Specifics
- [ ] Phase script starts with `ensure_core_path(__file__)` — no old Boundary-Safe Init block
- [ ] All file writes go through `AtomicWriter`
- [ ] All path access uses `self.dirs[key]` — zero hardcoded path strings
- [ ] Orchestrator calls `state_manager.sync_physical_files()` at startup
- [ ] Every completed phase calls `state_manager.update_task(..., "✅")`
- [ ] `StateManager` is instantiated with `skill_name=` parameter
- [ ] New config keys added to `config.yaml` under the correct section

#### Documentation
- [ ] `SKILL.md` or `ARCHITECTURE.md` updated if behaviour changed
- [ ] `DECISIONS.md` updated if a non-obvious design choice was made
- [ ] `CODING_GUIDELINES.md` updated if a new pattern was introduced

### 14.5 Running All Checks at Once

Add this to `ops/check.sh` for convenience:

```bash
#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$WORKSPACE"

echo "🔍 Ruff lint..."
ruff check .

echo "🎨 Ruff format check..."
ruff format --check .

echo "🔬 Mypy (core only)..."
mypy core/

echo "✅ All checks passed"
```

```bash
chmod +x ops/check.sh
./ops/check.sh
```

### 14.6 Recommended VS Code Extensions

Add `.vscode/extensions.json` to the repository root:

```json
{
  "recommendations": [
    "charliermarsh.ruff",           // Ruff linter + formatter
    "ms-python.mypy-type-checker",  // Mypy type checking
    "ms-python.python",             // Python language support
    "redhat.vscode-yaml",           // YAML schema validation
    "yzhang.markdown-all-in-one"    // Markdown preview & formatting
  ]
}
```

And `.vscode/settings.json`:

```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "charliermarsh.ruff",
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": "explicit",
      "source.organizeImports.ruff": "explicit"
    }
  },
  "python.analysis.typeCheckingMode": "basic",
  "files.trimTrailingWhitespace": true,
  "files.insertFinalNewline": true
}
```

