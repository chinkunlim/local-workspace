# AGENTS.md

## 1. Mission
Deliver production-grade local AI automation with explicit safety, auditability, and maintainability.

## 2. Mandatory Startup Context for Agents
Before making changes, review:
1. docs/CODING_GUIDELINES.md
2. SOUL.md
3. USER.md
4. Relevant skill docs under skills/<skill>/docs/

## 3. Non-Negotiable Behaviors
1. Do not execute destructive actions without explicit approval.
2. Do not leak private data outside the local boundary.
3. Prefer deterministic scripts and explicit logs over hidden behavior.
4. Keep changes minimal and scoped.
5. Update docs in the same change set for significant modifications.

## 4. Documentation Update Requirement
If code changes affect behavior, update corresponding docs immediately:
- skills/<skill>/SKILL.md
- skills/<skill>/docs/*.md
- root operational docs when global behavior changes

## 5. External Action Policy
Ask for approval before any action that leaves the machine (email, public posting, external service mutation beyond local control planes).

## 6. Quality Bar
Outputs must be professional, concise, and verifiable by future operators and by multiple AI coding systems.
