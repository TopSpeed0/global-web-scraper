import os
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(ROOT / "scripts"))


class FixtureHandler(SimpleHTTPRequestHandler):
    hits = {}

    def log_message(self, *args):
        pass

    def _send(self, status, body, headers=None):
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path.startswith("/status/"):
            code = int(path.rsplit("/", 1)[1])
            headers = {"Retry-After": "1"} if code == 429 else {}
            return self._send(code, f"<html><head><title>{code}</title></head><body>status {code}</body></html>", headers)
        if path.startswith("/empty-status/"):
            self.send_response(int(path.rsplit("/", 1)[1]))
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        if path == "/challenge":
            return self._send(403, (FIXTURES / "challenge.html").read_text(encoding="utf-8"))
        if path == "/flaky":
            count = FixtureHandler.hits.get(path, 0) + 1
            FixtureHandler.hits[path] = count
            if count == 1:
                return self._send(503, "<html><head><title>busy</title></head><body>busy</body></html>")
            return self._send(200, (FIXTURES / "quotes.html").read_text(encoding="utf-8"))
        return super().do_GET()


@pytest.fixture(scope="session")
def server():
    handler = partial(FixtureHandler, directory=str(FIXTURES))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


@pytest.fixture
def run_script():
    import json
    import subprocess

    def run(script, *args):
        proc = subprocess.run(
            [sys.executable, "-X", "utf8", str(ROOT / "scripts" / script), *args, "--json"],
            capture_output=True, text=True, encoding="utf-8", timeout=180,
            env={**os.environ, "NO_PROXY": "127.0.0.1,localhost"},
        )
        try:
            envelope = json.loads(proc.stdout)
        except json.JSONDecodeError:
            raise AssertionError(f"no JSON on stdout (exit {proc.returncode}):\n{proc.stdout}\n{proc.stderr}")
        return proc.returncode, envelope

    return run
