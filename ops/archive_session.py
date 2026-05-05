import os
import glob
import datetime
from pathlib import Path

def archive_current_session():
    brain_dir = os.path.expanduser("~/.gemini/antigravity/brain/")
    sessions_dir = "memory/sessions"
    os.makedirs(sessions_dir, exist_ok=True)
    
    # Find the most recently modified session in the brain
    latest_dir = None
    latest_time = 0
    for d in glob.glob(os.path.join(brain_dir, "*")):
        if os.path.isdir(d):
            overview_path = os.path.join(d, ".system_generated/logs/overview.txt")
            if os.path.exists(overview_path):
                mtime = os.path.getmtime(overview_path)
                if mtime > latest_time:
                    latest_time = mtime
                    latest_dir = d
                    
    if not latest_dir:
        print("No active AI session found.")
        return

    short_uuid = os.path.basename(latest_dir)[:8]
    date_str = datetime.datetime.fromtimestamp(latest_time).strftime('%Y-%m-%d')
    
    plan_file = os.path.join(latest_dir, "implementation_plan.md")
    walk_file = os.path.join(latest_dir, "walkthrough.md")
    task_file = os.path.join(latest_dir, "task.md")
    overview_file = os.path.join(latest_dir, ".system_generated/logs/overview.txt")
    
    plan_content = Path(plan_file).read_text() if os.path.exists(plan_file) else "*(No Implementation Plan)*"
    walk_content = Path(walk_file).read_text() if os.path.exists(walk_file) else "*(No Walkthrough)*"
    task_content = Path(task_file).read_text() if os.path.exists(task_file) else "*(No Task List)*"
    transcript = Path(overview_file).read_text() if os.path.exists(overview_file) else ""
    
    title = f"Session {short_uuid}"
    if os.path.exists(plan_file):
        lines = plan_content.split('\n')
        for line in lines:
            if line.startswith('# '):
                title = line.replace('# ', '').strip()
                break
    
    if title.startswith('Implementation Plan'):
        title = title.replace('Implementation Plan', '').strip('-: ')
    
    filename = f"{date_str}_{short_uuid}.md"
    out_path = os.path.join(sessions_dir, filename)
    
    content = f"""# {title}

> **Date:** {date_str}
> **Session ID:** `{short_uuid}`

---

## 1. Implementation Plan

{plan_content}

---

## 2. Walkthrough / Summary

{walk_content}

---

## 3. Tasks Executed

{task_content}

---

## 4. Raw Conversation Transcript

<details>
<summary>Click to expand full conversation log</summary>

```text
{transcript.replace('```', "'''")}
```
</details>
"""
    with open(out_path, 'w') as f:
        f.write(content)
    
    # Update HISTORY.md if not already there
    history_path = "memory/HISTORY.md"
    if os.path.exists(history_path):
        history_content = Path(history_path).read_text()
        entry = f"- **[{date_str}] [[Archived] {title}](sessions/{filename})** (ID: `{short_uuid}`)"
        if entry not in history_content:
            with open(history_path, 'a') as f:
                f.write(entry + "\n")
                
    print(f"Session {short_uuid} archived to {out_path} and HISTORY.md updated.")

if __name__ == "__main__":
    archive_current_session()
