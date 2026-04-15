# PDF Knowledge Walkthrough

## 1. Preconditions
1. Dependencies installed.
2. Config values set in skills/pdf-knowledge/config/config.yaml.
3. Security policy validated in skills/pdf-knowledge/config/security_policy.yaml.
4. Input PDFs placed in data/pdf-knowledge/input/01_Inbox.

## 2. Start Dashboard
Command:
python3 skills/pdf-knowledge/scripts/main_app.py

## 3. Process Queue via CLI
Command:
python3 skills/pdf-knowledge/scripts/queue_manager.py --process-all

Optional:
- --scan
- --process-one

## 4. Observe Outputs
- Processed: data/pdf-knowledge/output/02_Processed
- Agent core: data/pdf-knowledge/output/03_Agent_Core
- Final knowledge: data/pdf-knowledge/output/05_Final_Knowledge

## 5. Observe Logs and State
- System log: data/pdf-knowledge/logs/system.log
- Dashboard log: data/pdf-knowledge/logs/dashboard.log
- Resume artifacts: output/03_Agent_Core/<pdf_id>/resume_state.json

## 6. Resume After Interrupt
1. Restart dashboard or queue manager.
2. Inspect resume endpoint or interrupted state list.
3. Continue from recorded checkpoint without reprocessing completed chunks.
