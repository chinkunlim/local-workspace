# BOOTSTRAP.md

## 1. Purpose
Bring this workspace to an operational state on macOS with local-only services.

## 2. Environment Preparation
1. Install system dependencies:
   - brew install poppler tesseract tesseract-lang
2. Install Python dependencies:
   - cd open-claw-workspace
   - pip3 install -r requirements.txt
3. Optional browser automation dependency:
   - playwright install chromium

## 3. Service Boot
From local-workspace:
- ./start.sh

## 4. Service Stop
From local-workspace:
- ./stop.sh

## 5. Verification
1. Check logs directory for startup traces.
2. Verify open-claw-workspace skill runtime logs under data/<skill>/logs.
3. Confirm critical endpoints are reachable from start.sh output.

## 6. Documentation Baseline
After bootstrap, read and enforce:
- docs/CODING_GUIDELINES.md
- AGENTS.md
- skills/<skill>/SKILL.md
- skills/<skill>/docs/*.md
