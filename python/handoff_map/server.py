"""Local web server for the Handoff Map dashboard.

The page (static/index.html) has the same layout, styling and behavior as ../index.html. Parsing,
column grouping and every export (CSV, PNG, zip) run here in Python; the page only draws the results.
"""
from __future__ import annotations

import base64
import io
import json
import webbrowser
import zipfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .core import LEVELS, TYPE_GROUPS, Tab, Workflow, file_base, load_workflow, tab_csv, tab_levels
from .render import tab_png

STATIC = Path(__file__).resolve().parent / "static"
EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "loose-example.csv"
MAX_BODY = 50 * 1024 * 1024


def _tab(d: dict) -> Tab:
    if d.get("kind") not in ("tight", "loose", "all") or not d.get("files") or d.get("level", "task") not in LEVELS:
        raise ValueError("bad tab")
    files = [Workflow.from_dict(f) for f in d["files"]]
    for f in files:
        if f.category not in ("tight", "loose") or any(c.kind not in ("human", "ai", "handoff") for c in f.columns):
            raise ValueError("bad workflow")
    return Tab(str(d["id"]), str(d["title"]), d["kind"], files).at_level(d.get("level", "task"))


def parse_files(items: list[dict]) -> dict:
    """items: [{name, filename, data (base64)}] -> {workflows: [...], errors: [...]}"""
    workflows, errors = [], []
    for it in items:
        try:
            wf = load_workflow(it["filename"], base64.b64decode(it["data"]), it["name"])
            workflows.append(wf.to_dict())
        except Exception as err:  # bad encodings, corrupt xlsx, empty files
            errors.append(f"{it.get('filename', 'file')}: {err}")
    return {"workflows": workflows, "errors": errors}


def export(kind: str, tabs: list[Tab]) -> tuple[bytes, str, str]:
    """csv/png: the first tab at its own level. zip: every tab, once per level its files have."""
    if kind == "csv":
        return tab_csv(tabs[0]).encode("utf-8"), "text/csv; charset=utf-8", f"{file_base(tabs[0])}-visual.csv"
    if kind == "png":
        return tab_png(tabs[0]), "image/png", f"{file_base(tabs[0])}-visual.png"
    if kind == "zip":
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for t in (lv for tab in tabs for lv in tab_levels(tab)):
                z.writestr(f"{file_base(t)}-visual.csv", tab_csv(t))
                z.writestr(f"{file_base(t)}-visual.png", tab_png(t))
        return buf.getvalue(), "application/zip", "handoff-maps.zip"
    raise ValueError(f"unknown export type {kind!r}")


class Handler(BaseHTTPRequestHandler):
    server_version = "HandoffMap"

    def log_message(self, fmt, *args):  # keep the terminal quiet
        pass

    def _send(self, body: bytes, ctype: str, status=HTTPStatus.OK, filename: str | None = None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, status=HTTPStatus.OK):
        self._send(json.dumps(obj).encode("utf-8"), "application/json", status)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._send((STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/config":
            self._json({"typeGroups": TYPE_GROUPS, "hasExample": EXAMPLE.exists()})
        elif path == "/api/example" and EXAMPLE.exists():
            self._json(parse_files([{"name": "Example transcript", "filename": EXAMPLE.name,
                                     "data": base64.b64encode(EXAMPLE.read_bytes()).decode()}]))
        else:
            self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            return self._json({"error": "upload is too large"}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
            if self.path == "/api/parse":
                return self._json(parse_files(body["files"]))
            if self.path == "/api/export":
                data, ctype, name = export(body["kind"], [_tab(t) for t in body["tabs"]])
                return self._send(data, ctype, filename=name)
            self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        except (KeyError, TypeError, ValueError, IndexError) as err:
            self._json({"error": f"bad request ({err})"}, HTTPStatus.BAD_REQUEST)


def serve(host: str = "127.0.0.1", port: int = 8501, open_browser: bool = True) -> None:
    httpd = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{'localhost' if host in ('127.0.0.1', '0.0.0.0') else host}:{httpd.server_port}/"
    print(f"Handoff Map is running at {url}  (press Ctrl+C to stop)")
    if open_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
