"""fetch() against a local HTTP server: manifest recording, mismatch, archive-first."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
import requests

from weg.download.base import fetch
from weg.manifest import Manifest, ManifestMismatchError


class _Handler(BaseHTTPRequestHandler):
    content = {b"/a": b"hello", b"/slow": b"ok"}
    calls = []

    def do_GET(self):
        _Handler.calls.append(self.path)
        if self.path.startswith("/retry") and len([c for c in _Handler.calls if c.startswith("/retry")]) == 1:
            self.send_response(503)
            self.send_header("Retry-After", "0")
            self.end_headers()
            return
        body = _Handler.content.get(self.path.split("?")[0].encode(), b"retried")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def server():
    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def test_fetch_records_manifest_and_detects_change(server, tmp_path, monkeypatch):
    monkeypatch.delenv("HTTPS_PROXY", raising=False)
    monkeypatch.delenv("HTTP_PROXY", raising=False)
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    m = Manifest(tmp_path / "manifests" / "m.csv", root=tmp_path)
    raw = tmp_path / "data" / "raw"
    p = fetch(f"{server}/a", source="s", vintage="v1", name="a.txt", issue="t", raw_root=raw, manifest=m)
    assert p.read_bytes() == b"hello"
    row = m.lookup("s", f"{server}/a", "v1")
    assert row and row.raw_path == "data/raw/s/v1/a.txt"
    # same vintage, source now serves different bytes -> loud failure
    _Handler.content[b"/a"] = b"changed"
    with pytest.raises(ManifestMismatchError):
        fetch(f"{server}/a", source="s", vintage="v1", name="a.txt", issue="t", raw_root=raw, manifest=m, force=True)
    # new vintage is fine
    p2 = fetch(f"{server}/a", source="s", vintage="v2", name="a.txt", issue="t", raw_root=raw, manifest=m)
    assert p2.read_bytes() == b"changed"


def test_fetch_retries_on_503(server, tmp_path, monkeypatch):
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    m = Manifest(tmp_path / "manifests" / "m.csv", root=tmp_path)
    p = fetch(f"{server}/retry", source="s", vintage="v", name="r.txt", issue="t", raw_root=tmp_path / "raw", manifest=m)
    assert p.read_bytes() == b"retried"
