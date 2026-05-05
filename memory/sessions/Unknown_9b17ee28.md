# [Archived] Voice Memo Pipeline Architecture Refactoring

> **Date:** Unknown
> **Session ID:** `9b17ee28`

---

## 1. Implementation Plan

# Voice Memo Pipeline Architecture Refactoring

The current directory structure of the `scripts` folder is flat and mixes different operational concerns: core infrastructure, pipeline processing phases, orchestration, and standalone auxiliary tools. This makes the codebase unnecessarily complicated to navigate and breaks logical abstraction boundaries. 

The goal of this architectural change is to restructure the files by creating explicit boundaries for these components, enforcing consistent naming conventions, and reducing root-level clutter.

## User Review Required

> [!WARNING]
> This refactoring will change file paths and import paths within the project. The logic itself will remain exactly the same, but the way you execute standalone scripts might change slightly (e.g., `python scripts/utils/audit_tool.py` instead of `python scripts/audit_tool.py`).
> Do you approve of this new folder structure?

## Proposed Changes

We will group the files into `phases/` and `utils/`, update the `run_all.py` imports, and ensure `sys.path` handling so standalone scripts continue to work when executed directly.

### Main Scripts Directory
We will clean up the root `scripts/` folder so it only contains the orchestrator `run_all.py` and the `prompt.md` config file.

#### [MODIFY] [run_all.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/run_all.py)
- Update phase class import statements to reflect the new `phases/` structure (e.g. `from phases.phase0_glossary import Phase0Glossary`).

### Phases Directory
We will create a `phases/` directory to hold all the sequential pipeline steps and apply a consistent naming convention mapping to their logical progression (`phaseX_...`).

#### [NEW] [phases/\_\_init\_\_.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/phases/__init__.py)
#### [NEW] [phases/phase0_glossary.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/phases/phase0_glossary.py)
#### [DELETE] [glossary_tool.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/glossary_tool.py)
#### [NEW] [phases/phase1_transcribe.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/phases/phase1_transcribe.py)
#### [DELETE] [transcribe_tool.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/transcribe_tool.py)
#### [NEW] [phases/phase2_proofread.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/phases/phase2_proofread.py)
#### [DELETE] [proofread_tool.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/proofread_tool.py)
#### [NEW] [phases/phase3_merge.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/phases/phase3_merge.py)
#### [DELETE] [merge_tool.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/merge_tool.py)
#### [NEW] [phases/phase4_highlight.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/phases/phase4_highlight.py)
#### [DELETE] [highlight_tool.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/highlight_tool.py)
#### [NEW] [phases/phase5_synthesis.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/phases/phase5_synthesis.py)
#### [DELETE] [notion_synthesis.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/notion_synthesis.py)

*(All moved phase scripts will have `import sys, os; sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))` added to the top to ensure `from core import ...` works when executing independently. The class names inside will remain intact).*

### Utils Directory
We will move the standalone operational tools to a `utils/` directory to separate them from the pipeline phases.

#### [NEW] [utils/\_\_init\_\_.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/utils/__init__.py)
#### [NEW] [utils/audit_tool.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/utils/audit_tool.py)
#### [DELETE] [audit_tool.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/audit_tool.py)
#### [NEW] [utils/diff_tool.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/utils/diff_tool.py)
#### [DELETE] [diff_tool.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/diff_tool.py)
#### [NEW] [utils/subject_manager.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/utils/subject_manager.py)
#### [DELETE] [subject_manager.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/subject_manager.py)
#### [NEW] [utils/setup_wizard.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/utils/setup_wizard.py)
#### [DELETE] [setup_wizard.py](file:///Users/limchinkun/Desktop/local-workspace/open-claw-workspace/skills/voice-memo/scripts/setup_wizard.py)

*(All moved util scripts will dynamically adjust `SKILL_DIR` calculation to map correctly via `os.path.dirname(os.path.dirname(os.path.dirname(...)))` or similar, depending on their references to parent workspaces).*

## Open Questions

- None.

## Verification Plan

### Automated Tests
- Run `python3 scripts/run_all.py -h` to verify that imports and orchestration scripts bind correctly.
- Run `python3 scripts/utils/setup_wizard.py` to ensure it can still locate `config.json` properly.
- Verify `pylint` or simple manual syntax check doesn't report missing modules.


---

## 2. Walkthrough / Summary

# Architecture Restructuring Complete

The Voice Memo pipeline architecture has been completely overhauled to separate logical scripts, runtime data, and project documentation, preparing the workspace for future `skills`.

## Changes Made

### 1. Unified Logic `(skills/voice-memo)`
- Moved all development markdown files to a dedicated `docs/` folder.
- Refactored the flat `scripts/` directory into:
  - `core/`: State management, LLM endpoints
  - `phases/`: Pipeline steps sequentially named `phase0_glossary.py` through `phase5_synthesis.py`
  - `utils/`: Independent tools (`audit_tool.py`, `diff_tool.py`, `setup_wizard.py`)
- Python path configurations correctly locate imported files, meaning `utils` tools can still be executed independently.

### 2. Runtime Data Abstraction `(data/voice-memo/)`
- Moved all runtime-generated folders (`01_transcript` to `05_notion_synthesis`) into the global data sandbox instead of the project root.
- Relocated configuration `config.json` and system state files (`system.log`, `.pipeline_state.json`) to the data sandbox.
- Pipeline now securely points its operational `base_dir` toward `workspace/data/voice-memo/`.

## What Was Tested

- ✅ Python syntax compilation (`py_compile` on all modified files, successful)
- ✅ Path resolutions for nested `utils` to find `core` using auto-injected `sys.path.append()`.
- ✅ Data bindings checking that `BASE_DIR` respects the new `data/` destination layout.

## Next Step

The workspace is now clean with a strict separation of generic data and specific capabilities. You are ready to develop the second skill! All files for the new skill should reside in `skills/<new_skill>/`, and its processing target folder will naturally be resolved to `data/<new_skill>/`.


---

## 3. Tasks Executed

# Task List: Voice Memo Architecture Refactoring

- `[x]` Step 1: Directory Setup
  - `[x]` Create `skills/voice-memo/docs/`
  - `[x]` Create `skills/voice-memo/scripts/phases/`
  - `[x]` Create `skills/voice-memo/scripts/utils/`
  - `[x]` Create `data/voice-memo/`
- `[x]` Step 2: Documentation Migration
  - `[x]` Move management `.md` files from `voice-memo/` to `skills/voice-memo/docs/`
- `[x]` Step 3: Data & Config Migration
  - `[x]` Move `01_transcript`, `02_proofread`, `03_merged`, `04_highlighted`, `05_notion_synthesis`
  - `[x]` Move `raw_data`, `config.json`, `.pipeline_state.json`, `system.log`
  - `[x]` Delete obsolete folders (`transcript`, `proofread`, `notion_synthesis`)
  - `[x]` Remove old `voice-memo/` root folder
- `[x]` Step 4: Scripts Refactoring
  - `[x]` Move/Rename Phase scripts to `phases/phaseX_*.py`
  - `[x]` Add sys.path adjustments to Phase scripts
  - `[x]` Move Utility scripts to `utils/*_tool.py`
  - `[x]` Add sys.path adjustments to Utility scripts
- `[x]` Step 5: Path Updates
  - `[x]` Update `run_all.py` imports and orchestrator bindings
  - `[x]` Update `core/pipeline_base.py` for new `base_dir` resolution
  - `[x]` Update `setup_wizard.py` to point to new `config.json` location
  - `[x]` Update `subject_manager.py` internal paths
- `[x]` Step 6: Verify and Cleanup
  - `[x]` Dry-run `run_all.py -h` and tools to ensure no `ModuleNotFoundError`

