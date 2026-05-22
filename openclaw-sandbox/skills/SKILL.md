# Open Claw Skills

> Skills are modular, self-contained AI processing pipelines that share the `core/` framework.

## Available Skills

| Skill | Input | Output | Status |
|:---|:---|:---|:---:|
| [audio_transcriber](audio_transcriber/SKILL.md) | `.m4a` / `.mp3` audio recordings | Obsidian-ready `.md` knowledge notes | ✅ Production |
| [doc_parser](doc_parser/SKILL.md) | `.pdf`, `.pptx`, `.docx`, `.xlsx`, `.png` | Structured Markdown knowledge notes | ✅ Production |
| [proofreader](proofreader/SKILL.md) | `audio_transcriber` or `doc_parser` output | HITL-verified clean transcript (non-blocking) | ✅ Production |
| [smart_highlighter](smart_highlighter/SKILL.md) | Plain Markdown text | Highlight-annotated Markdown (Anti-Tampering) | ✅ Production (Standalone) |
| [note_generator](note_generator/SKILL.md) | Plain Markdown text | Structured YAML / Mermaid study notes | ✅ Production (Standalone) |
| [feynman_simulator](feynman_simulator/SKILL.md) | Verified Markdown from `04_final_verified/` | Socratic debate transcript + summary | ✅ Production |
| [academic_edu_assistant](academic_edu_assistant/SKILL.md) | Verified Markdown from `04_final_verified/` | Comparison report + Anki CSV | ✅ Production |
| [student_researcher](student_researcher/SKILL.md) | Multi-ingress (Chat MD / Telegram / Verified) | Academic claim verification report | ✅ Production (Manual Trigger) |
| [academic_library_agent](academic_library_agent/SKILL.md) | Claim list from `student_researcher` | PDF snapshots from academic databases | ✅ Production |
| [gemini_verifier_agent](gemini_verifier_agent/SKILL.md) | Claims + evidence from `student_researcher` | AI-debate Verification Report | ✅ Production |
| [knowledge_compiler](knowledge_compiler/SKILL.md) | All skill outputs | `data/wiki/` (Obsidian Vault) + ChromaDB | ✅ Production |
| [telegram_kb_agent](telegram_kb_agent/SKILL.md) | Telegram query via Open Claw | RAG text answer | ✅ Production |
| [interactive_reader](interactive_reader/SKILL.md) | Markdown with `> [AI:]` tags | In-place resolved annotations | ✅ Production |
| [inbox_manager](inbox_manager/SKILL.md) | `core/inbox_config.json` | Terminal output (routing rules) | ✅ Production |
| [video_ingester](video_ingester/SKILL.md) | Video files (`.mp4`, `.mov`, `.mkv`) | Illustrated Markdown transcript | ✅ Production (Standalone) |

## Standard Skill Directory Structure

Every skill follows this standardised layout:

```
skills/<skill-name>/
├── SKILL.md              # Quick-start guide (required)
├── manifest.py           # Open Claw skill registration (required)
├── config/
│   ├── config.yaml       # Paths, models, thresholds (required)
│   └── prompt.md         # LLM system prompt (if LLM-dependent)
├── docs/
│   ├── ARCHITECTURE.md   # Technical architecture document
│   ├── DECISIONS.md      # Architectural decision log (ADR format)
│   └── PROJECT_RULES.md         # AI collaboration context & constraints
└── scripts/
    ├── run_all.py         # Entry-point orchestrator
    └── phases/
        └── p<nn>_<name>.py  # Phase scripts (p00_, p01_, p02_ format)
```

## Creating a New Skill

### 1. Create Directories

```bash
mkdir -p skills/my_skill/{config,docs,scripts/phases}
```

### 2. Configure `config/config.yaml`

```yaml
paths:
  input:  "input/my_inbox"
  output: "output"
  state:  "state"
  logs:   "logs"
  phases:
    phase1: "output/01_result"
    phase2: "output/02_final"

runtime:
  ollama:
    api_url: "http://localhost:11434/api/generate"
    timeout_seconds: 600
```

### 3. Write a Phase Script

```python
# scripts/phases/p01_process.py
from core.utils.bootstrap import ensure_core_path
ensure_core_path(__file__)

from core import PipelineBase

class Phase1Process(PipelineBase):
    def __init__(self):
        super().__init__(
            phase_key="p1",
            phase_name="My Processing Phase",
            skill_name="my_skill"  # underscore, not hyphen (CODING_GUIDELINES §5.5)
        )
        # self.dirs["phase1"] is automatically resolved from config.yaml
```

### 4. Write `run_all.py`

Inherit `PipelineBase`. After `startup_check()`, call `self.state_manager.sync_physical_files()` to initialise progress tracking.

### 5. Register Routing Rule

Add the new skill's routing extension to `core/config/inbox_config.json` using `RouterAgent._build_routing_table()`.
Do NOT add routing logic directly to `core/services/inbox_daemon.py` (deprecated pattern as of V9.9).

To test routing: `uv run skills/inbox_manager/scripts/run_all.py --list`

## Global Conventions

- All phase scripts **must** start with: `from core.utils.bootstrap import ensure_core_path; ensure_core_path(__file__)`
- All paths accessed via `self.dirs[key]` — never hardcode paths.
- All file writes **must** use `core.utils.atomic_writer.AtomicWriter` to prevent partial-write corruption.
- After each phase completes, call: `self.state_manager.update_task(subject, filename, phase_key, "✅")`
- Use `core.utils.log_manager.build_logger()` — never use bare `print()` in production code.
