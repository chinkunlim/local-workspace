# Open Claw PKMS — Master Documentation Index

Welcome to the **Open Claw Personal Knowledge Management System (PKMS)** repository. 

This `INDEX.md` serves as the definitive map to the documentation ecosystem. Due to the complexity of a 9-skill multi-agent architecture, documentation is strictly layered to prevent entropy and confusion.

---

## 1. Global Navigation & Development Standards
These documents define the universal rules and layout of the entire `local-workspace/` monorepo.

- **[Coding Guidelines & Protocols](../docs/CODING_GUIDELINES.md)**: The Single Source of Truth (SSoT) for all AI and Human engineering rules. Includes the Anti-Truncation Protocol.
- **[System Structure Map](../docs/STRUCTURE.md)**: Annotated map of every critical file and folder.
- **[Technology Stack & Principles](../docs/OPENCLAW_TECH_STACK.md)**: Exhaustive reference of security defenses, multi-agent architecture, DAG states, and advanced Python implementations.
- **[Infrastructure Setup](../docs/INFRA_SETUP.md)**: Installation and configuration instructions for the underlying third-party infrastructure (Ollama, LM Studio, Open WebUI, LiteLLM, MCP Servers).
- **[User Manual](../docs/USER_MANUAL.md)**: High-level usage guide for human operators.
- **[Changelog](../CHANGELOG.md)**: The global chronological history of the project.

---

## 2. Active AI Agent Memory (`memory/`)
These files manage the state, context, and high-level architectural history of the ecosystem. AI Agents read these on every initialization.

- **[Global Architecture](../memory/ARCHITECTURE.md)**: Macro-level system diagram and service mapping.
- **[Global Decisions (ADR)](../memory/DECISIONS.md)**: A historical log of all major architectural design decisions, including integrated legacy analyses.
- **[Agent Behavior Contract](../memory/CLAUDE.md)**: Real-time context, environment rules, and hardware constraints.
- **[Task Tracker](../memory/TASKS.md)**: Live checklist of current and pending tasks.
- **[Handoff Log](../memory/HANDOFF.md)**: State preservation for cross-agent or cross-session continuation.

---

## 3. Sandbox Identity & Governance (`open-claw-sandbox/`)
The operational core of the Open Claw system contains identity bindings and operational checklists required to run the actual Python framework.

- **[Agent Authority](../open-claw-sandbox/AGENTS.md)**: Non-negotiable behaviors, external action policies, and documentation update matrices.
- **[Agent Identity](../open-claw-sandbox/IDENTITY.md)**: Formal identity definition of the Senior AI Systems Engineer.
- **[Persona & Soul](../open-claw-sandbox/SOUL.md)**: Aesthetic, tone, and ethical behavioral guidelines.
- **[User Context](../open-claw-sandbox/USER.md)**: Environmental context and preferences of the human operator (macOS, hardware limits).
- **[Bootstrap Guide](../open-claw-sandbox/BOOTSTRAP.md)**: Infrastructure startup scripts, dependency locking (`pip-tools`), and setup instructions.
- **[Tools Matrix](../open-claw-sandbox/TOOLS.md)**: Known network ports, URLs, and environment variables.
- **[Heartbeat Checklist](../open-claw-sandbox/HEARTBEAT.md)**: Operational health checks run at the start of any new session.

---

## 4. Skill-Level Architecture (The Tri-Document Suite)
Each of the 9 core skills inside `open-claw-sandbox/skills/` maintains absolute autonomy through a strict 3-file documentation set. Do not look in the root folder for skill-specific logic—always check the skill's `docs/` folder.

| Skill | Description | Documentation Suite |
|:---|:---|:---|
| **`audio_transcriber`** | Voice-to-Wiki pipeline | [Architecture](../open-claw-sandbox/skills/audio_transcriber/docs/ARCHITECTURE.md) \| [Claude](../open-claw-sandbox/skills/audio_transcriber/docs/CLAUDE.md) \| [Decisions](../open-claw-sandbox/skills/audio_transcriber/docs/DECISIONS.md) |
| **`doc_parser`** | PDF-to-Wiki extraction | [Architecture](../open-claw-sandbox/skills/doc_parser/docs/ARCHITECTURE.md) \| [Claude](../open-claw-sandbox/skills/doc_parser/docs/CLAUDE.md) \| [Decisions](../open-claw-sandbox/skills/doc_parser/docs/DECISIONS.md) |
| **`note_generator`** | Map-Reduce synthesis engine | [Architecture](../open-claw-sandbox/skills/note_generator/docs/ARCHITECTURE.md) \| [Claude](../open-claw-sandbox/skills/note_generator/docs/CLAUDE.md) \| [Decisions](../open-claw-sandbox/skills/note_generator/docs/DECISIONS.md) |
| **`smart_highlighter`** | Anti-tampering annotation | [Architecture](../open-claw-sandbox/skills/smart_highlighter/docs/ARCHITECTURE.md) \| [Claude](../open-claw-sandbox/skills/smart_highlighter/docs/CLAUDE.md) \| [Decisions](../open-claw-sandbox/skills/smart_highlighter/docs/DECISIONS.md) |
| **`knowledge_compiler`** | Glossary & WikiLink generator | [Architecture](../open-claw-sandbox/skills/knowledge_compiler/docs/ARCHITECTURE.md) \| [Claude](../open-claw-sandbox/skills/knowledge_compiler/docs/CLAUDE.md) \| [Decisions](../open-claw-sandbox/skills/knowledge_compiler/docs/DECISIONS.md) |
| **`interactive_reader`** | In-place annotation resolver | [Architecture](../open-claw-sandbox/skills/interactive_reader/docs/ARCHITECTURE.md) \| [Claude](../open-claw-sandbox/skills/interactive_reader/docs/CLAUDE.md) \| [Decisions](../open-claw-sandbox/skills/interactive_reader/docs/DECISIONS.md) |
| **`academic_edu_assistant`** | Anki export & Multi-doc RAG | [Architecture](../open-claw-sandbox/skills/academic_edu_assistant/docs/ARCHITECTURE.md) \| [Claude](../open-claw-sandbox/skills/academic_edu_assistant/docs/CLAUDE.md) \| [Decisions](../open-claw-sandbox/skills/academic_edu_assistant/docs/DECISIONS.md) |
| **`telegram_kb_agent`** | Telegram Bot RAG interface | [Architecture](../open-claw-sandbox/skills/telegram_kb_agent/docs/ARCHITECTURE.md) \| [Claude](../open-claw-sandbox/skills/telegram_kb_agent/docs/CLAUDE.md) \| [Decisions](../open-claw-sandbox/skills/telegram_kb_agent/docs/DECISIONS.md) |
| **`inbox_manager`** | CLI config route mutator | [Architecture](../open-claw-sandbox/skills/inbox_manager/docs/ARCHITECTURE.md) \| [Claude](../open-claw-sandbox/skills/inbox_manager/docs/CLAUDE.md) \| [Decisions](../open-claw-sandbox/skills/inbox_manager/docs/DECISIONS.md) |
| **`feynman_simulator`** | Multi-agent Socratic debate loop | [SKILL](../open-claw-sandbox/skills/feynman_simulator/SKILL.md) |
| **`video_ingester`** | Multimodal video processing pipeline | [SKILL](../open-claw-sandbox/skills/video_ingester/SKILL.md) |

> [!TIP]
> **To Developers & AI Agents:** Always consult this `INDEX.md` before generating new documentation. Ensure that any architectural shift is logged in the appropriate `DECISIONS.md` (global or skill-level) and that no history is ever deleted.
