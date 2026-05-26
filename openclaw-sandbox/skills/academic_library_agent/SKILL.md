---
name: academic_library_agent
description: Crosses paywalls and uses institutional login to fetch high-quality literature.
metadata:
  {
    "openclaw":
      {
        "emoji": "📚"
      }
  }
---

# Academic Library Agent

> **Pipeline**: Query Ingestion → Automated Login → PDF Extraction

## Quick Start

```bash
# Trigger the library agent to fetch pending literature
uv run skills/academic_library_agent/scripts/run_all.py --process-all
```

## Safety & Security Architecture

- **Credential Isolation**: Institutional login credentials must be stored securely in the `config_manager` encrypted vault, never in plaintext.
- **Rate Limiting**: Automated browser interactions contain strict exponential backoff and randomized jitters to avoid IP bans and comply with academic publisher rate limits.
- **Sandboxed Downloads**: All PDF downloads are routed strictly to `data/academic_library_agent/output/` using safe-path validation.

## Global Standards

- Uses `AtomicWriter` for all staging files.
