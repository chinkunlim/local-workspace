# PDF Knowledge Architecture Decisions

Last Updated: 2026-04-15

## Decision PK-001
Date: 2026-04-13
Decision: Execute lightweight diagnostic before deep extraction.
Rationale: Catch malformed, encrypted, or low-value cases before expensive processing.
Impact: Lower resource waste and earlier failure transparency.
Affected Files: pdf_diagnostic.py, queue_manager.py

## Decision PK-002
Date: 2026-04-13
Decision: Add vector chart supplementation path.
Rationale: Standard image extraction misses vector-only charts in many papers.
Impact: Better chart coverage and downstream analysis quality.
Affected Files: vector_chart_extractor.py

## Decision PK-003
Date: 2026-04-13
Decision: Add OCR confidence scoring pass.
Rationale: OCR uncertainty must be visible to operators and later synthesis steps.
Impact: Clear low-confidence page signaling and reduced silent corruption risk.
Affected Files: ocr_quality_gate.py

## Decision PK-004
Date: 2026-04-15
Decision: Align with shared core validation, logging, and CLI helper contracts.
Rationale: Reduce divergence from voice-memo and improve maintainability.
Impact: Cleaner governance and more predictable operations.
Affected Files: core/*, skills/pdf-knowledge/scripts/*
