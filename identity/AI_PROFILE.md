# Operator Profile & IDE AI Constraints

> **Target Audience:** Development AIs (Google Antigravity, Claude Code, GitHub Copilot)
> **Purpose:** Defines operator habits, IDE workflows, and the master entry sequence for developing this project.
## Identity
- **Role**: Operator & primary developer of the `local-workspace` monorepo
- **Working style**: Direct, precise, production-grade output only — no scaffolding, no stubs
- **Hardware**: macOS Apple Silicon, 16 GB RAM
- **Primary language for requests**: Traditional Chinese (zh-TW); documentation in English

---

## Communication & Workflow Habits

### How Jinkun gives instructions
- Uses short, high-context commands: `繼續`, `同步到github`, `更新implementation plan`
- **Workflow Macros**:
  - If Jinkun says `完成並同步` (Finish and Sync), the AI MUST automatically:
    1. Run `ops/check.sh` and `pytest tests/` to verify code correctness.
    2. Update any related `.md` files (`ARCHITECTURE.md`, `CHANGELOG.md`, etc.) to reflect the changes.
    3. Run `git add -A`, `git commit -m "..."`, and `git push` to GitHub.
- Frequently annotates via artifact comments instead of text messages
- Gives feedback mid-execution using inline comment annotations on the plan
- Switches between Chinese and English freely; code and docs should always be in English
- Uses `Continue` / `繼續` as the signal to proceed after plan approval — never re-explains

### Decision-making patterns
- Reviews implementation plans via artifact comments before approving execution
- Makes structural decisions through comments (e.g. "不需移動", "按建議移動")
- Often asks for updates to the plan before executing if scope changes
- Prefers conservative moves for high-risk changes (e.g. live service paths)
- Will explicitly state when something is safe to delete ("如果不再需要，可以刪除")

### Work session rhythm
- Works in focused sessions; uses `繼續` to resume after review
- Frequently checks Source Control (VS Code Git panel) after major changes
- Asks "還有pending changes?" to verify clean state before moving on
- Pushes to GitHub at end of meaningful milestones, not every commit

---

## Code & Architecture Preferences

### Structure
- Follows `CODING_GUIDELINES.md` as the single source of truth
- Expects AI to read guidelines first, then act — never guess the structure
- Strongly prefers `memory/` as AI reading layer (both global and per-sandbox)
- Config files (pyproject.toml, requirements.txt) must live at the relevant root, not in subdirs like `ops/config/`
- Dislikes wrapping layers that add no value (e.g. rejected `apps/` wrapper for single-app monorepo)

### Git discipline
- Conventional Commits format: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`
- One focused commit per logical change — no mega commits
- Commit messages must include a body explaining what and why, not just what
- Always pushes after commit — local-only commits are not acceptable
- `.DS_Store`, runtime logs, model caches, databases are NEVER committed

### Documentation discipline
- **Global Documentation Sync (SSoT)**: A code or structural change MUST be accompanied by updates to ALL relevant `.md` files in the same commit. Do not just update one file and ignore the rest. This includes, but is not limited to:
  - `memory/ARCHITECTURE.md` (if system architecture or logic changes)
  - `memory/HANDOFF.md` and `memory/TASKS.md` (at the end of every session or task completion)
  - `docs/STRUCTURE.md` and `docs/INDEX.md` (if any directory or file structure changes)
  - `CHANGELOG.md` (for any meaningful feature, fix, or refactor)
- **Continuous Principle Sync (主動原則更新)**: If Jinkun establishes a new operational principle, a new workflow habit, or gives a global instruction during the conversation, the AI **MUST proactively and automatically** integrate these new rules without asking.
  - To prevent writing to random files, you **MUST route the rule** according to this table:
    - **Operator Habits / Prompt Macros** ➡️ `identity/AI_PROFILE.md`
    - **Programming/Syntax/Formatting Standards** ➡️ `docs/CODING_GUIDELINES.md`
    - **IDE Hardware Limits / Execution Protocols** ➡️ `memory/PROJECT_RULES.md`
    - **Local Sandbox Agent Ethics/Boundaries** ➡️ `openclaw-sandbox/SOUL.md` or `openclaw-sandbox/IDENTITY.md`
    - **Why a technical approach was chosen** ➡️ `memory/DECISIONS.md`
  - **Principle Acknowledgement (強制確認)**: Every time the AI captures a new principle from the conversation, it **MUST explicitly state it** in the reply using this exact format:
    > `✅ 原則已記錄 → [target_file.md]：<rule content>`
    > This allows Jinkun to immediately verify the principle was captured correctly and routed to the right file. Silent updates are NOT acceptable.

---

## What AI Should NOT Do

### Execution prohibitions
- Do NOT modify files outside `openclaw-sandbox/` without explicit approval
- Do NOT run `start.sh` / `stop.sh` without asking first (services may be live)
- Do NOT assume a path exists — always `ls` or `cat` first
- Do NOT produce partial implementations without marking `# TODO(reason)` and explaining
- Do NOT auto-approve destructive operations (file deletion, directory removal)
- Do NOT commit runtime data, databases, model weights, or secret keys
- Do NOT invent environment variable names or config keys without reading existing files

### Documentation prohibitions
- Do NOT leave placeholder text in `.md` files (e.g. "存放你的個人偏好")
- Do NOT create empty stub docs — if a doc is created, it must have real content
- Do NOT update `HANDOFF.md` without updating the timestamp and session focus
- Do NOT mark a task complete in `TASKS.md` without verifying it is actually done

### AI behaviour prohibitions
- Do NOT ignore artifact comments — they are the primary feedback channel
- Do NOT re-explain the plan after the user says `繼續` — just execute
- Do NOT ask permission for safe read-only operations (ls, cat, grep, git status)
- Do NOT produce mega commits that mix unrelated changes

---

## AI Agent Master Startup Sequence (Mandatory)

> [!IMPORTANT]
> **To any AI Agent reading this:** You have been instructed to read this `AI_PROFILE.md` as your initial context. To safely operate this repository, you **MUST** read the following files in this exact order to build your full memory context before making any code changes:

1. **`memory/STARTUP.md`**: The canonical startup prompt and full session initialization process. Read this first to understand the complete workflow before proceeding.
2. **`docs/CODING_GUIDELINES.md`**: Read the entire file, paying special attention to **§15 AI-Native Documentation & Memory System** which explains the mandatory Append-Only rule and Historical Archival protocol.
3. **`memory/PROJECT_RULES.md`**: Your behaviour contract, environmental constraints, strict prohibitions, and the Code Review Checklist (§6).
4. **`memory/HANDOFF.md` & `memory/TASKS.md`**: The checkpoint of the previous AI session and your current pending tasks.
5. **`docs/STRUCTURE.md` & `docs/INDEX.md`**: The definitive maps of every directory and file in the workspace.
6. **`memory/DECISIONS.md` & `memory/HISTORY.md`**: Check these before proposing any architectural changes to understand past decisions and historical context.

**Do not guess the state of the project.** Read the files above to acquire your operational memory.