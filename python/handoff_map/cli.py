"""Batch export: python -m handoff_map transcript.csv [more.csv ...] -o out/"""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

from .core import base_name, file_base, load_workflow, make_tabs, tab_csv, tab_levels
from .render import tab_png


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="handoff_map", description="Export handoff maps as CSV and PNG files.")
    ap.add_argument("files", nargs="+", type=Path, help="transcript .csv or .xlsx files")
    ap.add_argument("-o", "--out", type=Path, default=Path("."), help="output folder (default: current folder)")
    ap.add_argument("--zip", action="store_true", help="write everything into handoff-maps.zip instead")
    ap.add_argument("--no-png", action="store_true", help="skip PNG files")
    args = ap.parse_args(argv)

    workflows, names = [], set()
    for path in args.files:
        try:
            name, i = base_name(path.name), 2
            while name in names:
                name, i = f"{base_name(path.name)} ({i})", i + 1
            wf = load_workflow(path.name, path.read_bytes(), name)
        except (OSError, ValueError) as err:
            print(f"Could not read {path}: {err}", file=sys.stderr)
            continue
        names.add(wf.name)
        workflows.append(wf)
        print(f"{wf.name}: {wf.category}, {len(wf.columns)} columns")
        for w in wf.warnings:
            print(f"  note: {w}")
    if not workflows:
        return 1

    outputs: list[tuple[str, bytes]] = []
    for tab in (t for tab in make_tabs(workflows) for t in tab_levels(tab)):
        outputs.append((f"{file_base(tab)}-visual.csv", tab_csv(tab).encode("utf-8")))
        if not args.no_png:
            outputs.append((f"{file_base(tab)}-visual.png", tab_png(tab)))

    args.out.mkdir(parents=True, exist_ok=True)
    if args.zip:
        target = args.out / "handoff-maps.zip"
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
            for name, data in outputs:
                z.writestr(name, data)
        print(f"Saved {target}")
    else:
        for name, data in outputs:
            (args.out / name).write_bytes(data)
            print(f"Saved {args.out / name}")
    return 0
