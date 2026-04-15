# -*- coding: utf-8 -*-
"""
main_app.py — PDF Knowledge Skill 主應用（最小可用版 V2.2）
============================================================
Flask 應用：Dashboard + 手動觸發 + resume_state 掃描

功能：
- GET  /              → Dashboard（佇列狀態、處理中、已完成、失敗隔離）
- POST /process       → 手動觸發 scan_inbox() + process_next()
- GET  /status        → JSON 狀態（供 Open Claw 查詢）
- GET  /resume        → 顯示所有未完成的 PDF
- POST /process/<id>  → 處理特定 PDF_ID
- GET  /api/source_preview → Voyager 懸浮預覽 API（Phase 5）

啟動方式：
  cd /path/to/open-claw-workspace
  python3 skills/pdf-knowledge/scripts/main_app.py

依賴：pip install flask pyyaml
"""

import os
import sys
import json

# --- Boundary-Safe Initialization ---
_script_dir = os.path.dirname(os.path.abspath(__file__))
_skill_root = os.path.dirname(os.path.dirname(_script_dir))  # skills/pdf-knowledge
_openclawed_root = os.path.dirname(_skill_root)  # open-claw-workspace
_core_dir = os.path.abspath(os.path.join(_openclawed_root, "core"))
_workspace_root = os.environ.get(
    "WORKSPACE_DIR",
    os.path.dirname(_openclawed_root)  # local-workspace
)

# Ensure WORKSPACE_DIR points to open-claw-workspace for config path resolution
if not os.path.isdir(os.path.join(os.environ.get("WORKSPACE_DIR", _workspace_root), "open-claw-workspace")):
    os.environ["WORKSPACE_DIR"] = _openclawed_root

# Enforce sandbox boundary: only core and this skill
# But preserve site-packages for third-party dependencies
_original_sys_path = sys.path.copy()
sys.path = [_core_dir, _script_dir] + [p for p in _original_sys_path if 'site-packages' in p or 'dist-packages' in p]

try:
    from flask import Flask, jsonify, request, render_template_string
except ImportError:
    print("❌ Flask 未安裝。請執行: pip install flask")
    sys.exit(1)

from core import ConfigManager, ResumeManager, ConfigValidator, build_logger


# ---------------------------------------------------------------------------- #
#  Config Loading                                                               #
# ---------------------------------------------------------------------------- #

_config_manager = ConfigManager(_openclawed_root, "pdf-knowledge")
_config = _config_manager.data

FLASK_HOST = ConfigValidator.require(_config_manager.get_nested("flask", "host"), "flask.host")
FLASK_PORT = ConfigValidator.require_int(_config_manager.get_nested("flask", "port"), "flask.port", min_value=1)
BASE_DIR = os.path.join(_openclawed_root, "data", "pdf-knowledge")
AGENT_CORE_DIR = os.path.join(BASE_DIR, "03_Agent_Core")
app = Flask(__name__)
resume_manager = ResumeManager(BASE_DIR)
dashboard_logger = build_logger(
    "OpenClaw.pdf-knowledge.dashboard",
    log_file=os.path.join(BASE_DIR, "logs", "dashboard.log"),
)


# ---------------------------------------------------------------------------- #
#  Dashboard Template                                                           #
# ---------------------------------------------------------------------------- #

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>OpenClaw PDF Knowledge — Dashboard</title>
  <style>
    body { font-family: 'SF Mono', monospace; background: #0d1117; color: #c9d1d9; margin: 0; padding: 24px; }
    h1 { color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 12px; }
    .section { margin: 24px 0; }
    h2 { color: #3fb950; font-size: 1em; text-transform: uppercase; letter-spacing: 0.1em; }
    .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; margin: 8px 0; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.85em; }
    .badge-done { background: #1a4731; color: #3fb950; }
    .badge-fail { background: #3d1f1f; color: #f85149; }
    .badge-pending { background: #282d38; color: #8b949e; }
    .badge-interrupted { background: #3d2b00; color: #e3b341; }
    table { width: 100%; border-collapse: collapse; font-size: 0.9em; }
    th { text-align: left; color: #8b949e; border-bottom: 1px solid #30363d; padding: 8px 4px; }
    td { padding: 6px 4px; border-bottom: 1px solid #21262d; }
    button { background: #238636; color: white; border: none; border-radius: 6px; padding: 8px 16px; cursor: pointer; }
    button:hover { background: #2ea043; }
    .btn-danger { background: #da3633; }
    .btn-danger:hover { background: #f85149; }
    code { background: #21262d; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }
    .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }
    .stat { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; text-align: center; }
    .stat-num { font-size: 2em; font-weight: bold; color: #58a6ff; }
    .stat-label { color: #8b949e; font-size: 0.85em; }
  </style>
</head>
<body>
  <h1>🧠 OpenClaw PDF Knowledge — Dashboard</h1>

  <div class="section">
    <div class="stat-grid">
      <div class="stat"><div class="stat-num">{{ stats.completed }}</div><div class="stat-label">✅ 已完成</div></div>
      <div class="stat"><div class="stat-num">{{ stats.interrupted }}</div><div class="stat-label">🔄 未完成</div></div>
      <div class="stat"><div class="stat-num">{{ stats.inbox }}</div><div class="stat-label">📥 Inbox 待處理</div></div>
    </div>
  </div>

  <div class="section">
    <h2>🔄 未完成的 PDF（可斷點續傳）</h2>
    {% if interrupted %}
    <table>
      <tr><th>PDF ID</th><th>上次 Phase</th><th>Chunk</th><th>儲存時間</th><th>操作</th></tr>
      {% for pdf_id, cp in interrupted.items() %}
      <tr>
        <td><code>{{ pdf_id }}</code></td>
        <td>{{ cp.phase }}</td>
        <td>{{ cp.chunk_index }}</td>
        <td>{{ cp.saved_at }}</td>
        <td>
          <form method="post" action="/process/{{ pdf_id }}" style="display:inline">
            <button type="submit">▶ 繼續</button>
          </form>
        </td>
      </tr>
      {% endfor %}
    </table>
    {% else %}
    <div class="card">📭 無未完成的 PDF</div>
    {% endif %}
  </div>

  <div class="section">
    <h2>📥 01_Inbox/ 佇列</h2>
    {% if inbox_files %}
    <table>
      <tr><th>檔案名稱</th><th>大小</th><th>操作</th></tr>
      {% for f in inbox_files %}
      <tr>
        <td>{{ f.name }}</td>
        <td>{{ f.size_mb }} MB</td>
        <td>
          <form method="post" action="/process" style="display:inline">
            <button type="submit">🚀 處理全部</button>
          </form>
        </td>
      </tr>
      {% endfor %}
    </table>
    {% else %}
    <div class="card">📭 Inbox 為空 — 請將 PDF 放入 <code>data/pdf-knowledge/01_Inbox/</code></div>
    {% endif %}
  </div>

  <div class="section">
    <h2>🛠️ 操作</h2>
    <div class="card">
      <form method="post" action="/process" style="display:inline">
        <button type="submit">🚀 掃描 Inbox + 處理所有 PDF</button>
      </form>
    </div>
    <div class="card" style="margin-top: 8px;">
      <a href="/status" style="color:#58a6ff;">📊 JSON 狀態 API</a> |
      <a href="/resume" style="color:#58a6ff;">🔄 未完成列表 API</a>
    </div>
  </div>

  <div class="section" style="color:#8b949e; font-size:0.8em;">
    OpenClaw PDF Knowledge V2.2 | Flask {{ flask_port }} | Core framework: shared core/
  </div>
</body>
</html>
"""


# ---------------------------------------------------------------------------- #
#  Route Helpers                                                                #
# ---------------------------------------------------------------------------- #

def _get_inbox_files():
    """List PDF files in inbox with size info."""
    inbox = os.path.join(BASE_DIR, "01_Inbox")
    if not os.path.exists(inbox):
        return []
    files = []
    for f in sorted(os.listdir(inbox)):
        if f.lower().endswith(".pdf"):
            path = os.path.join(inbox, f)
            size_mb = round(os.path.getsize(path) / (1024 * 1024), 2)
            files.append({"name": f, "size_mb": size_mb})
    return files


def _get_completed_count():
    """Count PDFs with raw_extracted.md."""
    processed = os.path.join(BASE_DIR, "02_Processed")
    if not os.path.exists(processed):
        return 0
    return sum(
        1 for d in os.listdir(processed)
        if os.path.exists(os.path.join(processed, d, "raw_extracted.md"))
    )


# ---------------------------------------------------------------------------- #
#  Routes                                                                       #
# ---------------------------------------------------------------------------- #

@app.route("/")
def dashboard():
    dashboard_logger.info("dashboard rendered")
    interrupted = resume_manager.get_all_interrupted()
    inbox_files = _get_inbox_files()
    stats = {
        "completed": _get_completed_count(),
        "interrupted": len(interrupted),
        "inbox": len(inbox_files),
    }
    return render_template_string(
        DASHBOARD_HTML,
        stats=stats,
        interrupted=interrupted,
        inbox_files=inbox_files,
        flask_port=FLASK_PORT,
    )


@app.route("/status")
def status():
    dashboard_logger.info("status requested")
    interrupted = resume_manager.get_all_interrupted()
    return jsonify({
        "skill": "pdf-knowledge",
        "version": "2.2",
        "stats": {
            "completed": _get_completed_count(),
            "interrupted": len(interrupted),
            "inbox": len(_get_inbox_files()),
        },
        "interrupted_pdfs": list(interrupted.keys()),
    })


@app.route("/resume")
def resume_list():
    dashboard_logger.info("resume list requested")
    interrupted = resume_manager.get_all_interrupted()
    return jsonify(interrupted)


@app.route("/process", methods=["POST"])
def process_all():
    """Trigger scan_inbox + process_all in background."""
    from threading import Thread

    dashboard_logger.info("process-all requested")

    def run():
        sys.path.insert(0, _script_dir)
        from queue_manager import QueueManager

        qm = QueueManager()
        qm.startup_check()
        qm.scan_inbox()
        qm.process_all()

    t = Thread(target=run, daemon=True)
    t.start()
    return jsonify({"status": "processing_started", "message": "Scan + process queue started in background"})


@app.route("/process/<pdf_id>", methods=["POST"])
def process_one(pdf_id: str):
    """Resume or re-process a specific PDF."""
    cp = resume_manager.check_resumable(pdf_id)
    action = "resume" if cp else "reprocess"
    dashboard_logger.info("process-one requested for %s (%s)", pdf_id, action)

    def run():
        sys.path.insert(0, _script_dir)
        from queue_manager import QueueManager

        qm = QueueManager()
        inbox = os.path.join(BASE_DIR, "01_Inbox")
        pdf_path = os.path.join(inbox, f"{pdf_id}.pdf")
        if not os.path.exists(pdf_path):
            print(f"⚠️ {pdf_id}.pdf 不在 Inbox，跳過")
            return
        qm._queue.append({
            "pdf_id": pdf_id,
            "pdf_path": pdf_path,
            "filename": f"{pdf_id}.pdf",
            "md5": qm._md5(pdf_path),
            "status": "pending",
        })
        qm.process_next()

    from threading import Thread

    t = Thread(target=run, daemon=True)
    t.start()
    return jsonify({"status": action, "pdf_id": pdf_id})


@app.route("/api/source_preview")
def source_preview():
    """
    [D023] Flask API for source snapshot hover preview.
    GET /api/source_preview?pdf_id=<id>&url=<url>
    Returns the screenshot image from 03_Agent_Core/{pdf_id}/verification/source_snapshots/
    """
    pdf_id = request.args.get("pdf_id", "")
    url = request.args.get("url", "")

    if not pdf_id or not url:
        return jsonify({"error": "pdf_id and url are required"}), 400

    import hashlib as hl
    url_hash = hl.md5(url.encode()).hexdigest()[:12]
    snapshots_dir = os.path.join(AGENT_CORE_DIR, pdf_id, "verification", "source_snapshots")

    # Look for matching screenshot
    if os.path.exists(snapshots_dir):
        for ext in [".png", ".jpg", ".webp"]:
            candidate = os.path.join(snapshots_dir, f"{url_hash}{ext}")
            if os.path.exists(candidate):
                from flask import send_file
                return send_file(candidate, mimetype=f"image/{ext.lstrip('.')}")

    return jsonify({"error": "snapshot not found", "url_hash": url_hash}), 404


# ---------------------------------------------------------------------------- #
#  Entry Point                                                                  #
# ---------------------------------------------------------------------------- #

if __name__ == "__main__":
    from core import build_skill_parser

    parser = build_skill_parser("PDF Knowledge Dashboard")
    parser.add_argument("--host", default=FLASK_HOST)
    parser.add_argument("--port", type=int, default=FLASK_PORT)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    print(f"\n🧠 OpenClaw PDF Knowledge Dashboard")
    print(f"   URL: http://{args.host}:{args.port}")
    print(f"   Base: {BASE_DIR}")
    print(f"   Inbox: {os.path.join(BASE_DIR, '01_Inbox')}")
    print(f"\n   將 PDF 放入 Inbox 後，開啟 http://{args.host}:{args.port} 操作\n")

    app.run(host=args.host, port=args.port, debug=args.debug)
