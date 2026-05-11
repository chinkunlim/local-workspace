# Security Policy

## Supported Versions

This is a private local workspace. There are no public releases.

## Reporting a Vulnerability

If you discover a security vulnerability (e.g., path traversal, credential exposure, sandbox escape), please:

1. **Do NOT open a public GitHub issue.**
2. Contact the workspace operator directly.
3. Provide a clear description of the issue and steps to reproduce.

## Security Principles

This workspace follows the security rules in `openclaw-sandbox/docs/CODING_GUIDELINES.md §7`:

- No credentials or API keys committed to git
- All file write operations use atomic write strategy
- PDF input files are immutable (never modified, only read)
- All pipeline outputs stay within `openclaw-sandbox/data/`
- No network calls outside the local sandbox without explicit operator approval
