"""Parsing, column grouping and CSV export for workflow transcripts.

This mirrors the logic in the browser dashboard (../index.html) so both
versions turn the same transcript into the same handoff map.
"""
from __future__ import annotations

import io
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

# ---------- Color key ----------
TYPE_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    ("Reviewing", [("Reviewing AI Reasoning", "FFC5B8"), ("Reviewing Proposed Courses", "FF7A5C"),
                   ("Reviewing Proposed Calendar", "FF542E"), ("Reviewing Plan Revisions", "FF2F00"),
                   ("Reviewing AI Self-Check Results", "D12600"), ("Assess Available Resources", "A31E00")]),
    ("Consulting", [("Consulting Degree Progress Record", "FFFDB8"), ("Consulting Course Sequence Guide", "FFFA5C")]),
    ("AI work", [("Black Box", "FFB8FB")]),
    ("Cross-checking", [("Cross-Checking Prerequisites", "D8FFB8"), ("Cross-Checking Course Availability", "A5FF5C"),
                        ("Cross-Checking Credit Load", "8CFF2E"), ("Cross-Checking Against AI Reasoning", "73FF00"),
                        ("Cross-Checking Against Degree Progress", "5ED100"),
                        ("Cross-Checking Against Recommended Sequence", "357500")]),
    ("Other human tasks", [("Pause", "C4C4C4"), ("Drafting Prompt", "525252"), ("Approving", "FFC28A"),
                           ("Submitting Final Plan", "FF7B00"), ("Orienting to Next Step", "00FFEA")]),
    ("Handoffs", [("General Request", "9FABEA"), ("Specific Request", "7486E0"), ("Direction to Check", "546AD9"),
                  ("Direction to Proceed", "2E49D1"), ("Intermediate Product", "263CAB"),
                  ("Complete Product", "152260")]),
]
UNKNOWN_HEX = "#FFFFFF"
KIND_LABEL = {"human": "Human", "ai": "AI", "handoff": "Handoff"}


def norm(s) -> str:
    s = re.sub(r"\s+", " ", str("" if s is None else s).strip()).lower()
    return re.sub("[‐-―]", "-", s)


COLORS: dict[str, str] = {}
CANON: dict[str, str] = {}
for _, _items in TYPE_GROUPS:
    for _name, _hex in _items:
        COLORS[norm(_name)] = "#" + _hex
        CANON[norm(_name)] = _name


# ---------- Data model ----------
@dataclass
class Cell:
    name: str
    hex: str
    known: bool


@dataclass
class Column:
    kind: str  # "human" | "ai" | "handoff"
    step: int
    label: str
    cells: list[Cell] = field(default_factory=list)


@dataclass
class Step:
    label: str
    start: int
    end: int


@dataclass
class Workflow:
    name: str
    category: str  # "tight" | "loose"
    columns: list[Column]
    steps: list[Step]
    warnings: list[str]
    counters: dict[str, int]
    id: str = field(default_factory=lambda: "w" + uuid.uuid4().hex[:7])

    @property
    def rows_max(self) -> int:
        return max((len(c.cells) for c in self.columns), default=0)

    def step_for(self, col_index: int) -> Step | None:
        return next((s for s in self.steps if s.start <= col_index <= s.end), None)

    def to_dict(self) -> dict:
        """JSON shape used by the dashboard page (same fields as the browser version)."""
        return {"id": self.id, "name": self.name, "category": self.category,
                "columns": [{"kind": c.kind, "step": c.step, "label": c.label,
                             "cells": [vars(x).copy() for x in c.cells]} for c in self.columns],
                "steps": [vars(s).copy() for s in self.steps], "warnings": list(self.warnings),
                "counters": dict(self.counters), "rowsMax": self.rows_max}

    @classmethod
    def from_dict(cls, d: dict) -> "Workflow":
        columns = [Column(c["kind"], int(c["step"]), c["label"],
                          [Cell(str(x["name"]), str(x["hex"]), bool(x["known"])) for x in c["cells"]])
                   for c in d["columns"]]
        steps = [Step(s["label"], int(s["start"]), int(s["end"])) for s in d["steps"]]
        return cls(d["name"], d["category"], columns, steps, list(d.get("warnings", [])),
                   dict(d["counters"]), d["id"])


# ---------- Parsing ----------
def parse_csv(text: str) -> list[list[str]]:
    """Read CSV text, guessing the delimiter (comma, semicolon or tab) from the first line."""
    text = text.lstrip("﻿")
    first = re.split(r"\r?\n", text, maxsplit=1)[0]
    counts = {d: first.count(d) for d in (",", ";", "\t")}
    delim = max(counts, key=lambda d: counts[d])
    rows, row, cell, quoted = [], [], "", False
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if quoted:
            if c == '"':
                if i + 1 < n and text[i + 1] == '"':
                    cell += '"'
                    i += 1
                else:
                    quoted = False
            else:
                cell += c
        elif c == '"':
            quoted = True
        elif c == delim:
            row.append(cell)
            cell = ""
        elif c in "\r\n":
            if c == "\r" and i + 1 < n and text[i + 1] == "\n":
                i += 1
            row.append(cell)
            rows.append(row)
            row, cell = [], ""
        else:
            cell += c
        i += 1
    if cell != "" or row:
        row.append(cell)
        rows.append(row)
    return rows


def parse_xlsx(data: bytes) -> list[list[str]]:
    from openpyxl import load_workbook

    ws = load_workbook(io.BytesIO(data), read_only=True, data_only=True).worksheets[0]
    return [["" if v is None else str(v) for v in r] for r in ws.iter_rows(values_only=True)]


def read_rows(filename: str, data: bytes) -> list[list[str]]:
    if re.search(r"\.xlsx?$", filename, re.I):
        rows = parse_xlsx(data)
    else:
        rows = parse_csv(data.decode("utf-8-sig", errors="replace"))
    if not rows or all(not str(v).strip() for r in rows for v in r):
        raise ValueError("the file is empty")
    return rows


def base_name(filename: str) -> str:
    return re.sub(r"\.(csv|xlsx|xls)$", "", Path(filename).name, flags=re.I)


def build_workflow(rows: list[list[str]], name: str) -> Workflow:
    warnings: list[str] = []
    rows = [["" if v is None else str(v).strip() for v in r] for r in rows]
    header = rows[0] if rows else []
    get = lambda r, i: r[i] if 0 <= i < len(r) else ""

    def find_col(pattern: str, fallback: int) -> int:
        return next((i for i, h in enumerate(header) if re.search(pattern, norm(h))), fallback)

    task_col, hand_col, agent_col = find_col("task", 1), find_col("hand", 2), find_col("agent", 3)
    if not any(re.search("task", norm(h)) for h in header):
        warnings.append("No “Task Type” header found, so columns B, C and D were read as "
                        "Task Type, Handoff Type and Agent.")

    has_step_labels = any(get(r, 0) != "" for r in rows[1:])
    cat_raw = norm(get(header, 0))
    if cat_raw.startswith("tight"):
        category = "tight"
    elif cat_raw.startswith("loose"):
        category = "loose"
    else:
        category = "tight" if has_step_labels else "loose"
        warnings.append(f"The first cell says “{get(header, 0) or '(blank)'}”. Treated as {category} because "
                        f"the file {'has' if has_step_labels else 'has no'} step labels.")

    # Flatten rows into a sequence of entries
    entries: list[tuple[str, str, int]] = []
    step_idx, step_labels = -1, []
    last_agent, inherited = None, 0
    for r in rows[1:]:
        if category == "tight" and get(r, 0):
            step_labels.append(get(r, 0))
            step_idx = len(step_labels) - 1
        task, hand, agent_raw = get(r, task_col), get(r, hand_col), norm(get(r, agent_col))
        if task:
            if re.search(r"\bai\b|^ai|artificial", agent_raw):
                kind = "ai"
            elif re.search("human|person|user", agent_raw):
                kind = "human"
            else:
                kind = last_agent or "human"
                inherited += 1
            last_agent = kind
            entries.append((kind, task, step_idx))
        if hand:
            entries.append(("handoff", hand, step_idx))
    if inherited:
        one = inherited == 1
        warnings.append(f"{inherited} task {'row has' if one else 'rows have'} no agent, so "
                        f"{'it was' if one else 'they were'} kept with the agent of the task above.")
    if category == "tight" and not step_labels:
        warnings.append("Marked Tight but no step labels were found in the first column.")
    if category == "tight" and any(step < 0 for _, _, step in entries):
        warnings.append("Some rows come before the first step label and sit outside any step.")

    # Group consecutive entries of the same kind within the same step
    counters = {"human": 0, "ai": 0, "handoff": 0}
    columns: list[Column] = []
    unknown: list[str] = []
    for kind, entry_name, step in entries:
        last = columns[-1] if columns else None
        if not last or last.kind != kind or last.step != step:
            counters[kind] += 1
            columns.append(Column(kind, step, f"{KIND_LABEL[kind]} #{counters[kind]}"))
        key = norm(entry_name)
        hex_ = COLORS.get(key)
        if not hex_ and entry_name not in unknown:
            unknown.append(entry_name)
        columns[-1].cells.append(Cell(CANON.get(key, entry_name), hex_ or UNKNOWN_HEX, bool(hex_)))
    if unknown:
        warnings.append(f"No color is set for: {', '.join(unknown)}. These show as striped squares "
                        f"and export as {UNKNOWN_HEX}.")

    steps: list[Step] = []
    if category == "tight":
        for i, label in enumerate(step_labels):
            idx = [j for j, c in enumerate(columns) if c.step == i]
            if idx:
                steps.append(Step(label, idx[0], idx[-1]))
            else:
                warnings.append(f"“{label}” has no rows under it.")
    return Workflow(name, category, columns, steps, warnings, counters)


def load_workflow(filename: str, data: bytes, name: str | None = None) -> Workflow:
    return build_workflow(read_rows(filename, data), name or base_name(filename))


# ---------- Tabs ----------
@dataclass
class Tab:
    id: str
    title: str
    kind: str  # "tight" | "loose" | "all"
    files: list[Workflow]


def ordered(workflows: list[Workflow]) -> list[Workflow]:
    return [w for w in workflows if w.category == "tight"] + [w for w in workflows if w.category == "loose"]


def make_tabs(workflows: list[Workflow]) -> list[Tab]:
    tabs = [Tab(w.id, w.name, w.category, [w]) for w in workflows]
    if len(workflows) > 1:
        tabs.append(Tab("all", "All workflows", "all", ordered(workflows)))
    return tabs


def groups_of(tab: Tab) -> list[tuple[str, list[Workflow]]]:
    groups = [(cat, [f for f in tab.files if f.category == cat]) for cat in ("tight", "loose")]
    return [g for g in groups if g[1]]


def legend_of(files: list[Workflow]) -> list[Cell]:
    seen: dict[str, Cell] = {}
    for f in files:
        for c in f.columns:
            for x in c.cells:
                seen.setdefault(x.name, x)
    return list(seen.values())


def slug(s: str) -> str:
    s = re.sub(r"\s+", "-", re.sub(r"[^\w\- ]+", "", s).strip())
    return s or "workflow"


def file_base(tab: Tab) -> str:
    return "all-workflows" if tab.id == "all" else slug(tab.title)


# ---------- CSV export ----------
def csv_cell(v) -> str:
    v = "" if v is None else str(v)
    return '"' + v.replace('"', '""') + '"' if re.search(r'[",\n\r]', v) else v


def step_row(f: Workflow) -> list[str]:
    out = [""] * len(f.columns)
    for s in f.steps:
        if s.start == s.end:
            out[s.start] = f"START/END: {s.label}"
        else:
            out[s.start] = f"START: {s.label}"
            out[s.end] = f"END: {s.label}"
    return out


def _pad(row: list[str], width: int) -> list[str]:
    return row + [""] * (width - len(row))


def block_matrix(f: Workflow, with_title: bool) -> list[list[str]]:
    """Rows of equal width for one workflow."""
    w = max(1, len(f.columns))
    rows = []
    if with_title:
        rows.append(_pad([f"{f.name} ({f.category})"], w))
    if f.category == "tight" or with_title:
        rows.append(_pad(step_row(f) if f.category == "tight" else [], w))
    rows.append(_pad([c.label for c in f.columns], w))
    for r in range(f.rows_max):
        rows.append(_pad([c.cells[r].hex if r < len(c.cells) else "" for c in f.columns], w))
    return rows


def tab_csv(tab: Tab) -> str:
    if tab.id != "all":
        grid = block_matrix(tab.files[0], False)
    else:
        # Workflows stacked top to bottom: tight group first, then loose
        w = max([1] + [len(f.columns) for f in tab.files])
        grid = []
        for gi, (cat, files) in enumerate(groups_of(tab)):
            if gi:
                grid += [[""] * w, [""] * w]
            grid.append(_pad([cat.upper()], w))
            for fi, f in enumerate(files):
                if fi:
                    grid.append([""] * w)
                grid += [_pad(r, w) for r in block_matrix(f, True)]
    lines = [",".join(csv_cell(v) for v in r) for r in grid]
    lines += ["", "Legend,Hex"] + [f"{csv_cell(x.name)},{x.hex}" for x in legend_of(tab.files)]
    return "\r\n".join(lines) + "\r\n"
