# PDF Knowledge Operational Spec

Version: V2.2
Last Updated: 2026-04-15

## 1. Objective
Extract, validate, and structure PDF knowledge with strict reproducibility, security boundaries, and operational traceability.

## 2. Runtime Contract
- Executor: local Python
- Dashboard: Flask
- LLM endpoint: runtime.ollama.api_url from skill config
- Config source: skills/pdf-knowledge/config/config.yaml
- Security policy source: skills/pdf-knowledge/config/security_policy.yaml

## 3. Phase Contract
1. Phase 1a diagnostic: low-cost structure and risk detection
2. Phase 1b extraction: deep content extraction and immutable artifact write
3. Phase 1c vector enrichment: non-raster chart recovery
4. Phase 1d OCR quality gate: confidence scoring and warnings
5. Queue management and resumable continuation

## 4. Must-Not Rules
1. Do not bypass security policy checks for browser actions.
2. Do not overwrite immutable extraction artifacts.
3. Do not skip resume-state updates on interruption paths.
4. Do not run heavy conflicting workloads concurrently when mutex denies access.

## 5. Operator Interface
Primary entry points:
- skills/pdf-knowledge/scripts/main_app.py
- skills/pdf-knowledge/scripts/queue_manager.py

## 6. Verification Checklist
1. Startup checks pass.
2. Security and dashboard logs are emitted.
3. Scan report and extraction artifacts exist and are consistent.
4. Resume behavior is deterministic after interruption.
