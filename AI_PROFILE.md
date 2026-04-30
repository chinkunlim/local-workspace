# Operator Profile — Jinkun

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
  - Skill-level `SKILL.md`, `ARCHITECTURE.md`, `CLAUDE.md`, `DECISIONS.md` (if a specific skill is modified)
  - `docs/USER_MANUAL.md` or `docs/INFRA_SETUP.md` (if user-facing operations or setup changes)
- **Continuous Profile Update**: When the user mentions new habits, workflows, or explicitly asks to "update md files" regarding their requirements, the AI MUST continuously integrate these new rules into `AI_PROFILE.md`.

---

## What AI Should NOT Do

### Execution prohibitions
- Do NOT modify files outside `open-claw-sandbox/` without explicit approval
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

## Workspace Entry Point (Mandatory Reading Order)
1. `memory/ARCHITECTURE.md` — global system overview
2. `open-claw-sandbox/memory/CLAUDE.md` — sandbox rules and behaviour contract
3. `open-claw-sandbox/AGENTS.md` — AI agent startup sequence
4. `docs/CODING_GUIDELINES.md` — development standards (v3.0.0)