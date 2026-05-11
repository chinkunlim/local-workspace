# Open Claw — Development Manual

> **Version**: V9.2 (Quality-First Model Optimization)
> **Last Updated**: 2026-05-05
> **Audience**: New and existing developers, AI agents, and open-source contributors

Welcome to the Open Claw Personal Knowledge Management System (PKMS). This manual is your chronological onboarding guide. The Open Claw architecture is highly disciplined, utilizing an Intent-Driven multi-agent orchestration pattern with strict data immutability and Single Responsibility rules.

To develop without friction, you must understand the core principles, the architectural layout, and the development workflow. This document stitches together the foundational guidelines.

---

## 1. The Path to Mastery (Required Reading)

Before writing a single line of code, you must consume the following documents in order. They are the Single Source of Truth (SSoT) for this ecosystem.

1. **[Global Architecture](../memory/ARCHITECTURE.md)**
   * **Why**: Gives you the 10,000-foot view. You will learn how the `RouterAgent` parses intents, how the `EventBus` auto-handoffs files between skills, and the boundaries between the `core/` framework and the `skills/` plugins.
2. **[Technology Stack & Principles](OPENCLAW_TECH_STACK.md)**
   * **Why**: Explains the *why* behind the architecture. It covers our OOM defenses (RAM Guard), our triple-defense anti-hallucination pipelines, SQLite semantic caching, and advanced Python invariants.
3. **[Coding Guidelines & Protocols](CODING_GUIDELINES.md)**
   * **Why**: The absolute law of the codebase. It covers our `core/` sub-package import rules (refactored on 2026-05-01), the Anti-Truncation Protocol, zero-temperature mandates, and strict Ruff/Mypy typing standards.

---

## 2. Developing a New Skill

Open Claw is an extensible platform. Adding a new capability means creating a new "Skill" in `openclaw-sandbox/skills/`.

### Step-by-Step Flow

1. **Initialize the Skill Directory**: 
   Create a new folder `skills/<skill_name>/` (use underscores, never hyphens).
2. **Create the Manifest**: 
   Every skill must have a `manifest.py` at its root. This registers the skill with the `SkillRegistry` and defines its trigger intents.
3. **Setup the Configuration**:
   Create `config/config.yaml` to define model profiles, VRAM thresholds, and phase-specific prompts.
4. **Implement the Phases**:
   Inside `scripts/phases/`, implement your phases (e.g., `p01_extract.py`). Every phase **must** inherit from `core.orchestration.pipeline_base.PipelineBase` and implement the `run()` method.
   * *Rule*: Always use `self.dirs["key"]` for paths. Never hardcode `/data/raw`.
   * *Rule*: Always use `AtomicWriter` for crash-safe file writes.
5. **Update State**:
   At the end of a successful phase execution, call `self.state_manager.update_task(...)` to record the completion in the DAG.
6. **Create the Orchestrator**:
   Create `scripts/run_all.py` which loads the phases and utilizes `run_skill_pipeline` to manage the execution flow.
7. **Document the Skill**:
   Create the strict Tri-Document Suite in the skill's `docs/` folder: `ARCHITECTURE.md`, `PROJECT_RULES.md`, and `DECISIONS.md`. Add a quick-start `SKILL.md` at the skill root.

---

## 3. Testing and Verification Workflow

Open Claw enforces strict quality gates. You cannot bypass them.

### Local Development Loop
When making changes, your development loop should look like this:

1. **Write Code**: Implement your feature or fix.
2. **Lint and Format**:
   ```bash
   cd openclaw-sandbox
   ruff check --fix .
   ruff format .
   ```
3. **Type Checking**:
   Ensure `mypy` passes with zero errors:
   ```bash
   cd openclaw-sandbox
   ./ops/check.sh
   ```
4. **Run Unit Tests**:
   Tests are located in `openclaw-sandbox/tests/`. Ensure you mock dependencies correctly using the full sub-package path (e.g., `@patch("core.orchestration.task_queue.subprocess.run")`).
   ```bash
   cd openclaw-sandbox
   PYTHONPATH=. pytest tests/ -q
   ```

### The Global Quality Gate
Before any Git commit, you **must** run the global check script from the repository root:
```bash
./ops/check.sh
```
This script performs a full monorepo scan, including Shellcheck for bash scripts, Ruff/Mypy for Python, and a credential leakage scan.

---

## 4. Documentation Maintenance (The SSoT Rule)

Code changes are only 50% of the job. The other 50% is ensuring the documentation reflects the new state perfectly. 

If you add a new feature, module, or skill, you must update:
1. `CHANGELOG.md`
2. `docs/STRUCTURE.md` (if a file/folder was added)
3. `memory/ARCHITECTURE.md` (if the system architecture shifted)
4. `memory/DECISIONS.md` (Log an ADR explaining *why* you made the technical choice)

> [!WARNING]
> **Anti-Truncation Protocol**: Never delete historical records in `DECISIONS.md`. If a pattern is deprecated, mark it `[ABANDONED]` and provide reasoning.

---

## 5. Deployment and Operations

The Open Claw environment is managed via headless infrastructure scripts in the `infra/` directory.

- **Start Services**: `./infra/scripts/start.sh` (Bootstraps Ollama, LiteLLM, Inbox Daemon, Scheduler)
- **Stop Services**: `./infra/scripts/stop.sh`
- **Check Status**: `./ops/check.sh`
- **Monitor Queue**: `tail -f openclaw-sandbox/logs/task_queue.log`

For operational usage instructions, refer to the **[User Manual](USER_MANUAL.md)**.
