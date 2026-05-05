# Open Claw — Doc Parser Skill Architecture

> Version: V3.0 | Last Updated: 2026-05-01

## 1. Overview

The Doc Parser skill is Open Claw's PDF-to-knowledge pipeline. It automatically extracts, analyses, and synthesises PDF documents — including VLM image analysis — into structured Markdown knowledge notes.

```
data/raw/<subject>/<pdf_name>.pdf
          │
          ▼ P00a: Lightweight diagnostic (page count, text density, scan detection)
          │
          ▼ P01a: Docling deep extraction → raw_extracted.md (IMMUTABLE)
          │
          ├──► P01b: Vector chart rasterisation (pdftoppm @ 300 DPI)
          │
          └──► P01c: OCR quality gate (triggered only for scanned PDFs)
          │
          ▼ P01d: VLM visual figure analysis (updates figure_list.md)
          │
          ▼ P02: Highlight annotations (delegated to smart_highlighter)
          ▼ P03: Synthesis (delegated to note_generator → data/wiki/)
```

---

## 2. Directory Structure

```
skills/doc_parser/
├── SKILL.md                       # Quick-start guide
├── config/
│   ├── config.yaml                # Paths, models, concept constraints (skill-specific only)
│   ├── prompt.md                  # Phase 1d/0a LLM instruction templates (zero hardcoding)
│   ├── priority_terms.json        # Cross-skill terminology protection list
│   ├── security_policy.yaml       # PDF security scanning rules
│   └── selectors.yaml             # Data source selectors
├── docs/
│   ├── ARCHITECTURE.md            # This file
│   ├── DECISIONS.md               # Architectural decision log (ADR format)
│   └── PROJECT_RULES.md                  # AI collaboration context
└── scripts/
    ├── run_all.py                  # Orchestrator — queue-based 7-phase executor
    └── phases/
        ├── p00a_diagnostic.py     # Phase 00a: Lightweight PDF diagnostic
        ├── p01a_engine.py         # Phase 01a: Docling deep extraction
        ├── p01b_vector_charts.py  # Phase 01b: Vector chart supplementation (300 DPI)
        ├── p01c_ocr_gate.py       # Phase 01c: OCR quality gate
        └── p01d_vlm_vision.py     # Phase 01d: VLM image analysis
```

---

## 3. Subject-Based Directory Hierarchy

The Doc Parser inbox and output are both layered by subject:

```
data/doc_parser/
├── input/
│   └── 01_Inbox/
│       ├── AI_Papers/          ← subject folder
│       │   ├── attention.pdf
│       │   └── bert.pdf
│       └── Physics/
│           └── quantum.pdf
└── output/
    ├── error/<subject>/<pdf_id>/     # Failed processing
    ├── vector_db/                    # ChromaDB vector database
    └── library/                      # Document archive
```

---

## 4. Core Architecture Principles

### 4.1 Inheritance Chain

```python
from core.utils.bootstrap import ensure_core_path
ensure_core_path(__file__)

from core.orchestration.pipeline_base import PipelineBase

class Phase01bPDFEngine(PipelineBase):
    def __init__(self) -> None:
        super().__init__(
            phase_key="phase1b",
            phase_name="Docling Deep Extraction",
            skill_name="doc_parser"
        )
        # self.dirs["processed"] → data/doc_parser/output/01_processed
        # self.dirs["final"]     → data/doc_parser/output/03_synthesis
```

### 4.2 Config-Driven Path Resolution

```yaml
# skills/doc_parser/config/config.yaml
paths:
  input:  "input/01_Inbox"
  output: "output"
  state:  "state"
  logs:   "logs"
  phases:
    inbox:       "input/01_Inbox"
    processed:   "output/01_processed"
    error:       "output/error"
    vector_db:   "output/vector_db"
    library:     "output/library"
```

### 4.3 State Tracking

- `core.state.state_manager.StateManager(skill_name="doc_parser")` manages 5-phase progress
- Phase set: `["p0a", "p1a", "p1b", "p1c", "p1d"]`
- `data/doc_parser/state/checklist.md` tracks processing status for every PDF

### 4.4 IMMUTABLE Source Rule

`output/01_processed/<subject>/<pdf_id>/raw_extracted.md` is the raw Docling output and **must never be overwritten**. All subsequent AI-processed results are written to `output/03_synthesis/`, ensuring full traceability and rollback capability.

### 4.5 Global Config Layering

```
core/config/global.yaml                     ← Hardware thresholds + Ollama runtime
    ↓ deep-merge
skills/doc_parser/config/config.yaml        ← Skill-specific overrides
```

`ConfigManager._deep_merge()` ensures skill config overrides global defaults safely.

### 4.6 Zero Hardcoded Prompts

All LLM prompts are stored in `config/prompt.md` and loaded by `PipelineBase.get_prompt(section_title)` using `## Section Title` parsing. Modifying prompts **requires no Python code changes**.

---

## 5. Orchestrator Queue Mechanism

`run_all.py`'s `QueueManager` inherits `PipelineBase` and is responsible for:

1. Recursively scanning `01_Inbox/<subject>/` to discover unprocessed PDFs
2. MD5 deduplication (prevents reprocessing identical files)
3. `ModelMutex` ensures Docling is never used concurrently
4. Writing `StateManager.update_task()` after each phase to update `checklist.md`
5. Supports `--interactive` mode that pauses after P1d for manual figure verification

---

## 6. Core Framework Dependencies

| Core Module | Usage in Doc Parser |
|:---|:---|
| `core.orchestration.pipeline_base.PipelineBase` | Base class for all Phase classes |
| `core.config.config_manager.ConfigManager` | Loads and deep-merges `global.yaml` + `config.yaml` |
| `core.state.state_manager.StateManager` | P0a–P1d progress tracking |
| `core.utils.path_builder.PathBuilder` | Resolves directories from `config.yaml` |
| `core.ai.llm_client.OllamaClient` | P1d VLM inference (llama3.2-vision) |
| `core.services.security_manager.SecurityManager` | PDF security scan before P0a |
| `core.utils.glossary_manager.GlossaryManager` | Syncs terminology from audio_transcriber |
| `core.services.inbox_daemon.SystemInboxDaemon` | Watches `01_Inbox/` for new PDFs |

---

## 7. CLI Usage

```bash
cd open-claw-sandbox

# Process all PDFs in the Inbox
python3 skills/doc_parser/scripts/run_all.py --process-all

# Process only a specific subject
python3 skills/doc_parser/scripts/run_all.py --subject AI_Papers

# Interactive mode (pause after P1d for figure verification)
python3 skills/doc_parser/scripts/run_all.py --interactive

# Force re-run on all files
python3 skills/doc_parser/scripts/run_all.py --process-all --force

# Switch LLM model profile
python3 core/cli/cli_config_wizard.py --skill doc_parser
```

---

## 8. Feature Parity with Audio Transcriber

| Feature | Audio Transcriber | Doc Parser |
|:---|:---:|:---:|
| Subject-based hierarchy | ✅ | ✅ |
| StateManager progress tracking | ✅ P1–P3 | ✅ P0a–P1d |
| Config-driven paths | ✅ | ✅ |
| InboxDaemon monitoring | ✅ | ✅ |
| Checkpoint Resume | ✅ | ✅ |
| IMMUTABLE raw output | ✅ P1 | ✅ P1a |
| VLM image analysis | — | ✅ P1d |
| OCR quality gate | — | ✅ P1c |
| Anti-hallucination defense | ✅ Triple-layer | — |
