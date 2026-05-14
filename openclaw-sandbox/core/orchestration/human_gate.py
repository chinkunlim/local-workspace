"""
human_gate.py — Universal Verification Gate (Ephemeral WebUI)
=============================================================
Provides a strictly isolated, ephemeral WebUI for Human-in-the-Loop verification.
Pauses the pipeline, serves a side-by-side Diff, and resumes once the human submits.
Zero external dependencies (uses standard library http.server).
"""

import html
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import re
import socket
import threading
from typing import Optional

from rich import print


class _GatedHTTPServer(HTTPServer):
    """HTTPServer subclass that carries a typed `gate` attribute."""

    gate: "VerificationGate"


class VerificationGateHandler(BaseHTTPRequestHandler):
    """Handles HTTP requests for the ephemeral WebUI."""

    server: _GatedHTTPServer  # type: ignore[override]

    def log_message(self, format, *args):  # noqa: A002
        # Suppress default HTTP logging to keep CLI clean
        pass

    def do_GET(self):
        """Serve the UI or the audio file."""
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            page = self.server.gate.generate_html()
            self.wfile.write(page.encode("utf-8"))
        elif self.path.startswith("/audio"):
            audio_path = self.server.gate.audio_path
            if not audio_path or not os.path.exists(audio_path):
                self.send_response(404)
                self.end_headers()
                return
            try:
                with open(audio_path, "rb") as f:
                    self.send_response(200)
                    self.send_header("Content-type", "audio/mp4")  # m4a/mp4
                    self.end_headers()
                    self.wfile.write(f.read())
            except Exception:
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        """Handle the submit action."""
        if self.path == "/submit":
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(post_data)
                final_text = data.get("text", "")
                self.server.gate.final_text = final_text

                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode("utf-8"))

                # Signal the server to shutdown
                threading.Thread(target=self.server.shutdown, daemon=True).start()
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


class VerificationGate:
    def __init__(
        self,
        skill_name: str,
        original_text: str,
        llm_text: str,
        audio_path: Optional[str] = None,
        port: int = 8080,
        reference_text: str = "",
    ):
        self.skill_name = skill_name
        self.original_text = original_text
        self.llm_text = llm_text
        self.audio_path = audio_path
        self.reference_text = reference_text
        self.final_text: Optional[str] = None

        # Resolve port conflict
        self.port = self._find_free_port(port)

    def _find_free_port(self, start_port: int) -> int:
        port = start_port
        while port < start_port + 100:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("localhost", port)) != 0:
                    return port
            port += 1
        return start_port

    def _parse_original_text_to_html(self, text: str) -> str:
        """Parse custom [? word | timestamp ?] tags into clickable spans."""
        # Escape HTML entities first
        escaped = html.escape(text)
        # Replace newlines with <br>
        escaped = escaped.replace("\n", "<br>")
        # Convert [? word | 12.5 ?] → clickable span
        pattern = re.compile(r"\[\?\s*(.*?)\s*\|\s*([\d.]+)\s*\?\]")

        def repl(match: re.Match) -> str:
            word = match.group(1)
            ts = match.group(2)
            return f'<span class="uncertain" onclick="playAudio({ts})">{word}</span>'

        return pattern.sub(repl, escaped)

    def generate_html(self) -> str:
        left_html = self._parse_original_text_to_html(self.original_text)
        right_html_json = json.dumps(self.llm_text)
        ref_html = html.escape(self.reference_text).replace("\n", "<br>")

        audio_section = ""
        if self.audio_path:
            audio_section = (
                '<div class="audio-container">'
                "<h3>Source Audio</h3>"
                '<audio id="player" controls style="width: 100%;">'
                '<source src="/audio" type="audio/mp4">'
                "Your browser does not support the audio element."
                "</audio>"
                "</div>"
            )

        has_ref = bool(self.reference_text)
        has_ref_json = json.dumps(has_ref)

        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Verification Gate | Open Claw</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #1e1e1e; color: #d4d4d4; margin: 0; padding: 20px; display: flex; flex-direction: column; height: 100vh; box-sizing: border-box; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333; padding-bottom: 10px; margin-bottom: 15px; flex-shrink: 0; }}
        .btn {{ background: #007acc; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-size: 16px; font-weight: bold; }}
        .btn:hover {{ background: #005999; }}
        .top-container {{ display: flex; gap: 20px; margin-bottom: 15px; flex-shrink: 0; }}
        .audio-container {{ flex: 1; background: #252526; padding: 15px; border-radius: 6px; border: 1px solid #333; }}
        .audio-container h3 {{ margin-top: 0; color: #9cdcfe; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }}
        .main-container {{ display: flex; gap: 20px; flex: 1; min-height: 0; }}
        .pane {{ display: flex; flex-direction: column; background: #252526; border: 1px solid #333; border-radius: 6px; padding: 15px; overflow-y: auto; }}
        .pane-left {{ flex: 1; }}
        .pane-center {{ flex: 1.5; }}
        .pane-right {{ flex: 1; display: none; }}
        .pane h3 {{ margin-top: 0; margin-bottom: 10px; color: #9cdcfe; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; display: flex; justify-content: space-between; align-items: center; }}
        .content {{ font-family: Consolas, "Courier New", monospace; font-size: 14px; line-height: 1.6; white-space: pre-wrap; }}
        #editor {{ flex: 1; width: 100%; border: 1px solid #3c3c3c; }}
        .uncertain {{ background: #795e26; color: white; padding: 2px 4px; border-radius: 3px; cursor: pointer; border: 1px solid #cca700; }}
        .uncertain:hover {{ background: #cca700; color: black; }}
        .toggle-btn {{ background: #333; color: #ccc; border: 1px solid #555; padding: 6px 12px; border-radius: 3px; cursor: pointer; font-size: 14px; }}
        .toggle-btn:hover {{ background: #444; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>Open Claw Verification Gate <span style="font-size: 14px; color: #808080;">({self.skill_name})</span></h2>
        <div>
            <button class="toggle-btn" id="ref-toggle-btn" onclick="toggleRef()" style="margin-right: 10px;">Toggle Reference Panel</button>
            <button class="btn" onclick="submit()">Approve &amp; Resume Pipeline</button>
        </div>
    </div>
    <div class="top-container" id="top-bar">
        {audio_section}
    </div>
    <div class="main-container">
        <div class="pane pane-left">
            <h3>Raw Output (Immutable)</h3>
            <div class="content">{left_html}</div>
        </div>
        <div class="pane pane-center">
            <h3>
                <span>Ollama Correction (Markdown Edit)</span>
                <span style="font-size:11px; font-weight:normal; color:#888; text-transform:none;">Select text -> Right Click -> "Replace All"</span>
            </h3>
            <div id="editor"></div>
        </div>
        <div class="pane pane-right" id="ref-pane">
            <h3>📚 References (PDF & Glossary)</h3>
            <div class="content">{ref_html}</div>
        </div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.41.0/min/vs/loader.min.js"></script>
    <script>
        function playAudio(time) {{
            const player = document.getElementById('player');
            if (player) {{
                player.currentTime = Math.max(0, time - 2);
                player.play();
            }}
        }}

        function toggleRef() {{
            const refPane = document.getElementById('ref-pane');
            if (refPane.style.display === 'none' || refPane.style.display === '') {{
                refPane.style.display = 'flex';
            }} else {{
                refPane.style.display = 'none';
            }}
            // Trigger Monaco editor resize
            if (editorInstance) {{
                setTimeout(() => editorInstance.layout(), 50);
            }}
        }}

        if (!{has_ref_json}) {{
            document.getElementById('ref-toggle-btn').style.display = 'none';
        }}

        let editorInstance = null;

        require.config({{ paths: {{ 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.41.0/min/vs' }} }});
        require(['vs/editor/editor.main'], function() {{
            editorInstance = monaco.editor.create(document.getElementById('editor'), {{
                value: {right_html_json},
                language: 'markdown',
                theme: 'vs-dark',
                wordWrap: 'on',
                minimap: {{ enabled: false }},
                fontSize: 14,
                lineHeight: 1.6,
                fontFamily: 'Consolas, "Courier New", monospace',
                automaticLayout: true
            }});

            editorInstance.addAction({{
                id: 'replace-all-custom',
                label: 'Replace All (Global)',
                contextMenuGroupId: 'modification',
                contextMenuOrder: 1.5,
                run: function(ed) {{
                    const selection = ed.getSelection();
                    const text = ed.getModel().getValueInRange(selection);
                    if (!text) {{
                        alert("Please select some text first.");
                        return;
                    }}
                    const replacement = prompt(`Replace all occurrences of "\\n${{text}}\\n" with:`);
                    if (replacement !== null) {{
                        const model = ed.getModel();
                        const fullText = model.getValue();
                        const escapeRegExp = (string) => string.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&');
                        const regex = new RegExp(escapeRegExp(text), 'g');
                        const count = (fullText.match(regex) || []).length;

                        if (count > 0 && confirm(`Found ${{count}} occurrences. Replace all?`)) {{
                            const newText = fullText.replace(regex, replacement);
                            model.setValue(newText);
                        }}
                    }}
                }}
            }});
        }});

        async function submit() {{
            if (!editorInstance) return;
            const text = editorInstance.getValue();
            const btn = document.querySelector('.btn');
            btn.innerText = "Saving...";
            btn.disabled = true;
            try {{
                const res = await fetch('/submit', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ text: text }})
                }});
                if (res.ok) {{
                    document.body.innerHTML = "<h2 style='text-align:center;margin-top:20vh;color:#4CAF50;'>Verification Complete!</h2><p style='text-align:center;'>You can close this tab. The pipeline will now resume.</p>";
                }} else {{
                    alert("Failed to submit.");
                    btn.innerText = "Approve & Resume Pipeline";
                    btn.disabled = false;
                }}
            }} catch (e) {{
                alert("Error: " + e);
                btn.innerText = "Approve & Resume Pipeline";
                btn.disabled = false;
            }}
        }}
    </script>
</body>
</html>"""

    def start(self) -> str:
        """Start the ephemeral WebUI, block until the user submits, return the final text."""
        server = _GatedHTTPServer(("localhost", self.port), VerificationGateHandler)
        server.gate = self

        msg = f"  \U0001f449 ACTION REQUIRED: Open http://localhost:{self.port} to verify output."
        try:
            from rich.console import Console
            from rich.panel import Panel

            Console().print(
                Panel(msg, title="[bold yellow]Verification Gate Paused", border_style="yellow")
            )
        except ImportError:
            print("\n" + "=" * 60)
            print(" \u26a0\ufe0f VERIFICATION GATE PAUSED")
            print(msg)
            print("=" * 60 + "\n")

        # Blocks until server.shutdown() is called inside the POST handler
        server.serve_forever()

        return self.final_text or ""
