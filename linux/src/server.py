"""Embedded HTTP/REST server providing API endpoints and Web UI for KnowYourClicks.

Pure Python standard library (http.server.ThreadingHTTPServer). Zero external dependencies.
"""

import json
import mimetypes
import urllib.parse
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

from .config import BASE_DIR
from .db import Database
from .input_listener import InputListener
from .privacy_filter import PrivacyFilter
from .speed_tracker import SpeedTracker
from .text_expander import TextExpander

WEB_DIR = BASE_DIR / "src" / "web"


class APIRequestHandler(SimpleHTTPRequestHandler):
    """Handles REST API requests and serves web assets."""

    def __init__(self, *args, **kwargs):
        self.db = Database()
        self.speed_tracker = SpeedTracker()
        self.input_listener = InputListener()
        self.text_expander = TextExpander(self.db)
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def _send_json(self, data: dict, status: int = HTTPStatus.OK):
        """Sends a JSON response with CORS headers."""
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        """Handles CORS preflight."""
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Handles GET requests for API and static files."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # API: Statistics
        if path == "/api/stats":
            timeframe = query.get("timeframe", ["1h"])[0]
            stats = self.db.get_statistics(timeframe)
            return self._send_json({"success": True, "data": stats})

        # API: Shortcuts
        if path == "/api/shortcuts":
            shortcuts = self.db.get_shortcuts()
            return self._send_json({"success": True, "data": shortcuts})

        # API: Speed prompts
        if path == "/api/speed/prompts":
            prompts = self.speed_tracker.get_sample_prompts()
            return self._send_json({"success": True, "data": prompts})

        # API: Speed test status
        if path == "/api/speed/status":
            status = self.speed_tracker.get_status()
            return self._send_json({"success": True, "data": status})

        # API: Speed test history
        if path == "/api/speed/history":
            history = self.db.get_recent_speed_sessions(limit=15)
            return self._send_json({"success": True, "data": history})

        # API: System status
        if path == "/api/system/status":
            listener_status = self.input_listener.get_status()
            return self._send_json({
                "success": True,
                "data": {
                    "daemon_running": True,
                    "listener": listener_status,
                    "active_speed_test": self.speed_tracker.get_status()["active"]
                }
            })

        # Default static file serving (index.html, style.css, app.js)
        if path == "/" or not path:
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        """Handles POST requests for mutations and actions."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            payload = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            payload = {}

        # API: Dispatch Key (enforces privacy whitelist)
        if path == "/api/key":
            key_name = payload.get("key", "")
            char_val = payload.get("char", "")
            result = self.input_listener.dispatch_software_key(key_name, char_val)
            return self._send_json({"success": True, "processed": result is not None, "data": result})

        # API: Expand Text on Space Trigger
        if path == "/api/expand":
            text = payload.get("text", "")
            new_text, expanded, trigger, rep = self.text_expander.process_text_on_space(text)
            return self._send_json({
                "success": True,
                "text": new_text,
                "expanded": expanded,
                "trigger": trigger,
                "replacement": rep
            })

        # API: Create / Update Shortcut
        if path == "/api/shortcuts":
            shortcut = payload.get("shortcut", "")
            replacement = payload.get("replacement", "")
            ok = self.db.add_shortcut(shortcut, replacement)
            return self._send_json({"success": ok, "message": "Shortcut saved" if ok else "Invalid shortcut data"})

        # API: Start Speed Test
        if path == "/api/speed/start":
            mode = payload.get("mode", "given_text")
            duration = int(payload.get("duration", 60))
            status = self.speed_tracker.start_session(mode, duration)
            return self._send_json({"success": True, "data": status})

        # API: Finish Given Text Speed Test
        if path == "/api/speed/finish":
            prompt = payload.get("prompt", "")
            typed = payload.get("typed", "")
            elapsed = float(payload.get("elapsed", 60.0))
            result = self.speed_tracker.finish_given_text_session(prompt, typed, elapsed)
            return self._send_json({"success": True, "data": result})

        # API: Stop Speed Test
        if path == "/api/speed/stop":
            status = self.speed_tracker.stop_session()
            return self._send_json({"success": True, "data": status})

        return self._send_json({"success": False, "error": "Not Found"}, status=HTTPStatus.NOT_FOUND)

    def do_DELETE(self):
        """Handles DELETE requests (e.g. removing shortcuts)."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/shortcuts/"):
            try:
                shortcut_id = int(path.split("/")[-1])
                ok = self.db.delete_shortcut(shortcut_id)
                return self._send_json({"success": ok})
            except Exception as e:
                return self._send_json({"success": False, "error": str(e)}, status=HTTPStatus.BAD_REQUEST)

        return self._send_json({"success": False, "error": "Not Found"}, status=HTTPStatus.NOT_FOUND)


def run_server(host: str = "127.0.0.1", port: int = 45678):
    """Starts the HTTP server."""
    server = ThreadingHTTPServer((host, port), APIRequestHandler)
    print(f"[KnowYourClicks Server] Running at http://{host}:{port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
