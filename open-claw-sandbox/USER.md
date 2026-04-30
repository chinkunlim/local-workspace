# USER.md

## User Profile

- **Timezone**: Asia/Taipei (UTC+8)
- **Hardware**: MacBook with Apple Silicon, 16 GB RAM
- **Primary language**: Traditional Chinese (zh-TW), technical communication in English

## Working Preferences

1. **Clean architecture.** Explicit structure, no hidden coupling, no magic paths.
2. **Strict naming consistency.** File names, config keys, and variable names must match across code, config, and documentation.
3. **Complete logging and explicit records.** Every runtime action must be traceable from logs alone.
4. **Production-grade AI coding output.** No prototypes, no placeholders, no TODO stubs without a documented plan.
5. **Sandbox isolation.** The open-claw-sandbox must remain fully self-contained. No cross-boundary references.
6. **English-first documentation.** All technical docs and code comments in English. User-facing intent phrases may be bilingual.

## Communication Preferences

- Provide concise, high-signal updates during implementation.
- Provide an explicit summary of all changes made after completing a task.
- State blockers and open questions directly — do not bury them in narrative text.
- Use exact file paths and script names in all references. Never use vague descriptions like "the config file."

## Approval Requirements

The following require explicit user approval before execution:
- Any file deletion
- Any move or rename of files outside the `open-claw-sandbox/` directory
- Any external network action (API call, browser automation to non-local endpoint)
- Any change to `skills/doc_parser/config/security_policy.yaml`
- Any change to `skills/doc_parser/config/priority_terms.json`
