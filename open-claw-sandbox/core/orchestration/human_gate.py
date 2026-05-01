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
    ):
        self.skill_name = skill_name
        self.original_text = original_text
        self.llm_text = llm_text
        self.audio_path = audio_path
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
        right_html = html.escape(self.llm_text)

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

        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Verification Gate | Open Claw</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #1e1e1e; color: #d4d4d4; margin: 0; padding: 20px; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333; padding-bottom: 10px; margin-bottom: 20px; }}
        .btn {{ background: #007acc; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-size: 16px; font-weight: bold; }}
        .btn:hover {{ background: #005999; }}
        .container {{ display: flex; gap: 20px; height: calc(100vh - 150px); }}
        .pane {{ flex: 1; display: flex; flex-direction: column; background: #252526; border: 1px solid #333; border-radius: 6px; padding: 15px; overflow-y: auto; }}
        .pane h3 {{ margin-top: 0; color: #9cdcfe; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }}
        .content {{ font-family: Consolas, "Courier New", monospace; font-size: 14px; line-height: 1.6; white-space: pre-wrap; }}
        textarea {{ flex: 1; background: #1e1e1e; color: #d4d4d4; border: 1px solid #3c3c3c; padding: 10px; font-family: Consolas, "Courier New", monospace; font-size: 14px; line-height: 1.6; resize: none; outline: none; }}
        textarea:focus {{ border-color: #007acc; }}
        .uncertain {{ background: #795e26; color: white; padding: 2px 4px; border-radius: 3px; cursor: pointer; border: 1px solid #cca700; }}
        .uncertain:hover {{ background: #cca700; color: black; }}
        .audio-container {{ margin-bottom: 20px; background: #252526; padding: 15px; border-radius: 6px; border: 1px solid #333; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>Open Claw Verification Gate <span style="font-size: 14px; color: #808080;">({self.skill_name})</span></h2>
        <button class="btn" onclick="submit()">Approve &amp; Resume Pipeline</button>
    </div>
    {audio_section}
    <div class="container">
        <div class="pane">
            <h3>Raw Output (Immutable)</h3>
            <div class="content">{left_html}</div>
        </div>
        <div class="pane">
            <h3>Ollama Correction (Edit Below)</h3>
            <textarea id="llm-text">{right_html}</textarea>
        </div>
    </div>
    <script>
        function playAudio(time) {{
            const player = document.getElementById('player');
            if (player) {{
                player.currentTime = Math.max(0, time - 2);
                player.play();
            }}
        }}
        async function submit() {{
            const text = document.getElementById('llm-text').value;
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
