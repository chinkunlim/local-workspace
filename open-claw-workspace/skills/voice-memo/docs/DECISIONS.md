# Voice Memo Architecture Decisions

Last Updated: 2026-04-15

## Decision VM-001
Date: 2026-04-07
Decision: Split previous monolithic flow into explicit five-phase pipeline.
Rationale: Reduce context pollution and improve deterministic debugging.
Impact: Cleaner phase ownership, easier resume and failure isolation.
Affected Files: skills/voice-memo/scripts/phases/*, skills/voice-memo/scripts/run_all.py

## Decision VM-002
Date: 2026-04-12
Decision: Move orchestration concerns into shared core OOP base.
Rationale: Remove repeated boilerplate and normalize reliability behavior.
Impact: Lower maintenance cost and easier cross-skill consistency.
Affected Files: core/pipeline_base.py, core/state_manager.py, core/llm_client.py

## Decision VM-003
Date: 2026-04-15
Decision: Adopt canonical input/output/state/logs data semantics with migration compatibility.
Rationale: Standardize future skill onboarding and reduce path ambiguity.
Impact: Requires migration script usage and alias compatibility checks.
Affected Files: core/path_builder.py, core/data_layout.py, migrate_data_layout.py

## Decision VM-004
Date: 2026-04-15
Decision: Enforce config validation for required runtime and hardware parameters.
Rationale: Prevent hidden runtime drift caused by missing or malformed configuration.
Impact: Startup fails fast on invalid config.
Affected Files: core/config_validation.py, core/pipeline_base.py
