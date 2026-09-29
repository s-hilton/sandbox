"""Handoff Map dashboard. Run with: python app.py  (then open http://localhost:8501)"""
import argparse

from handoff_map.server import serve

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Start the Handoff Map dashboard.")
    ap.add_argument("--port", type=int, default=8501, help="port to listen on (default 8501)")
    ap.add_argument("--host", default="127.0.0.1", help="address to bind (default 127.0.0.1, this computer only)")
    ap.add_argument("--no-browser", action="store_true", help="don't open a browser window")
    args = ap.parse_args()
    serve(args.host, args.port, not args.no_browser)
