# Workflow Map

A single-page dashboard (`index.html`) that turns workflow transcript CSVs into color-coded handoff maps.

- **Left panel:** upload one or more `.csv` (or `.xlsx`) transcripts, review parse notes, and download results.
- **Right panel:** one tab per uploaded workflow, plus an **All workflows** tab that stacks every workflow top to bottom (tight first, then loose) once two or more are loaded.

## Input format

Cell A1 says `Tight` or `Loose`. The header row names an optional `Micro Task` column, `Task Type`, an optional `Macro Task` column, `Handoff Type` and `Agent`. For tight workflows, step labels (e.g. `Step 1: Propose`) go in column A on the first row of each step. See `examples/micro-example.csv` (all three levels; the example the dashboard opens with), `examples/loose-example.csv` and `examples/tight-example.csv`.

## Micro tasks, task types and macro tasks

- **Micro Task** (left of Task Type) has one action per row. A row with a micro task and no task type belongs to the task type above it. A micro task with no task type above it (e.g. `SESSION_START`, which marks that data collection has begun) is a micro task only: it shows in the micro view and the all-levels view's Micro column, with nothing beside it, and has no task type or macro task.
- **Macro Task** (between Task Type and Handoff Type) goes on the first task row it covers; leave the rows below it blank until the next one starts.

Each map has a **Micro tasks / Task types / Macro tasks / All levels** switch (only the levels the file has are shown). Every view keeps the same columns and handoffs. **All levels** splits each human and AI column into Micro, Task and Macro sub-columns with one row per micro task; task and macro squares stretch down the rows they cover, so you can read across to see which task type and macro task each micro task belongs to. Hover any square to see what it includes and belongs to. Macro names that are also task types (e.g. `Black Box`, `Submitting Final Plan`) keep the same color; micro tasks use their own neon colors (see the color key).

## How columns are built

Consecutive rows of the same kind become one column: human tasks → `Human #n`, AI tasks → `AI #n`, handoffs → `Handoff #n`. A task row with no agent stays with the agent of the task above it. Groups never cross a step boundary.

## Exports

Each tab exports as `<name>-visual.csv` (one hex color code per square, step START/END markers above the headers, legend below) and `<name>-visual.png`. When the files have micro or macro tasks, every download also saves `<name>-micro-visual`, `<name>-macro-visual` and `<name>-all-levels-visual` (CSV and PNG) for the levels they have. In the all-levels CSV a tall square repeats its color on each row it covers.

Open `index.html` directly in a browser to use it locally.

## Python version

The `python/` folder has a Python version of the same dashboard (`python app.py`), dark by default with a light/dark toggle, plus a command-line exporter that writes the same CSV and PNG files. See `python/README.md`.
