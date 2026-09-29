# Workflow Map

A single-page dashboard (`index.html`) that turns workflow transcript CSVs into color-coded handoff maps.

- **Left panel:** upload one or more `.csv` (or `.xlsx`) transcripts, review parse notes, and download results.
- **Right panel:** one tab per uploaded workflow, plus an **All workflows** tab that stacks every workflow top to bottom (tight first, then loose) once two or more are loaded.

## Input format

Cell A1 says `Tight` or `Loose`. The header row names `Task Type`, `Handoff Type` and `Agent`. For tight workflows, step labels (e.g. `Step 1: Propose`) go in column A on the first row of each step. See `examples/tight-example.csv`.

## How columns are built

Consecutive rows of the same kind become one column: human tasks → `Human #n`, AI tasks → `AI #n`, handoffs → `Handoff #n`. A task row with no agent stays with the agent of the task above it. Groups never cross a step boundary.

## Exports

Each tab exports as `<name>-visual.csv` (one hex color code per square, step START/END markers above the headers, legend below) and `<name>-visual.png`.

Open `index.html` directly in a browser to use it locally.

## Python version

The `python/` folder has a Python version of the same dashboard (`python app.py`), dark by default with a light/dark toggle, plus a command-line exporter that writes the same CSV and PNG files. See `python/README.md`.
