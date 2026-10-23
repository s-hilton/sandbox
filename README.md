# Workflow Map

A single-page dashboard (`index.html`) that turns workflow transcript CSVs into color-coded handoff maps.

- **Left panel:** upload one or more coded transcripts (`.numbers`, `.xlsx` or `.csv`), review parse notes, and download results.
- **Right panel:** one tab per uploaded workflow, plus an **All workflows** tab that stacks every workflow top to bottom (tight first, then loose) once two or more are loaded, and a **Statistics** tab.

## Input format

Cell A1 says `TIGHT` or `LOOSE`. The header row below it has `Time`, `Phase`, `Actions`, `Task Types`, `Handoff Type`, `Reasoning to Move Forward` and `Agent` (column order doesn't matter). Upload Numbers (`.numbers`), Excel (`.xlsx`) or CSV files. See `examples/tight-session.csv` and `examples/loose-session.csv`, the two examples the dashboard opens with.

- **Time** is minutes.seconds: `24.05` is 24:05 and `25.1` is 25:10. Clock times like `24:05` also work. Each row lasts until the next row with a time; a time earlier than the row above it is flagged and left out of time measures.
- **Phase** labels (e.g. `Step 1: Propose`) go on the first row of each phase and draw a bracket over its columns.
- **Actions** has one action per row. A row with an action and no task type belongs to the task above it. An action with no task type above it (e.g. `SESSION_START`) is an action only.
- **Task Types** starts a new task on the row it is named.
- **Action families** and **task families** are filled in from the codebook below, so they don't need their own columns. If a sheet has `Action Family` or `Task Family` columns, those are used instead.
- **Reasoning to Move Forward** goes on the row where the person moved on (usually `APPROVE`).
- **Agent** can be left blank to keep the agent of the row above; AI and system actions (`SESSION_START`, `AI_WORKING`, …) need none.
- Codes ignore case, spaces and underscores, and a small typo (`READ_AI_OUPUT`) is read as the closest code and noted on the left. `Direction Check` is read as `Direction to Check`.

## Codebook and colors

| Action family | Actions |
| --- | --- |
| LOOK_AT_AI | READ_AI_OUTPUT, OPEN_AI_REASONING, OPEN_AI_CHANGES, OPEN_SCHEDULE_VIEW, OPEN_ITEM_DETAIL |
| LOOK_AT_RECORDS | OPEN_REFERENCE, READ_REFERENCE |
| CROSS_REFERENCE | MOVE_BETWEEN_SOURCES |
| HOUSEKEEPING | CLOSE_VIEW, PAUSE |
| TALK_TO_AI | COMPOSE_PROMPT, SEND_PROMPT |
| AI_OR_SYSTEM | SESSION_START, AI_WORKING, AI_OUTPUT, SYSTEM_ERROR |
| CONTROL_WORKFLOW | APPROVE, GO_BACK |

| Task family | Task types |
| --- | --- |
| GATHER | UNDERSTAND_OUTPUT, BUILD_OWN_STANDARD |
| JUDGE | CHECK_AGAINST_RECORDS, CHECK_AI_ITSELF, JUDGE_BY_FEEL |
| STEER | CORRECT_AI, REDIRECT_OR_DELEGATE |
| PROCEED | AUTHORIZE |
| NON_TASK | NON_TASK |
| BLACK_BOX | BLACK_BOX |

Reasoning to move forward: OWN_CHECK, PRIOR_CHECK, LOOKS_RIGHT, REQUEST_HONORED, RATIONALE, DELEGATED, CARRIED_TRUST, AI_ASSURANCE, RESIGNATION. Handoffs keep their colors.

Each family has its own hue, and its actions or task types are lighter and darker shades of it, so you can read across levels. The family hues and the reasoning colors were checked for colorblind separation. Every code has its own hex, so a CSV of hex codes can always be read back. The full list with hex codes is under **Color key** in the dashboard.

## Levels

Each map has an **Actions / Action families / Task types / Task families / All levels** switch, and the **All workflows** tab has one switch that sets every map at once. **All levels** splits each human and AI column into Action, Action family, Task, Task family and Reason sub-columns with one row per action; task squares stretch down the rows of their actions. In the other levels, a dot on a square's corner is the reasoning to move forward coded on it. Hover any square to see its codes, time, duration and source row.

## Statistics tab

Once transcripts are loaded, a **Statistics** tab works through the question *How do people convince themselves that they can move forward (accept, continue or submit AI output)?*, comparing tight with loose sessions:

- **Overview**: headline numbers and a timeline of every session, colored by any level, with each decision to move forward marked by its reasoning.
- **1 · Quantity**: the mix of human tasks or actions (by count or time) in each workflow. χ² test with a permutation p-value, Cramér's V and adjusted residuals, plus a session-level Mann–Whitney U for each category.
- **2 · Process**: transition grids (which task follows which), a χ² test of whether the paths differ, what came right before each decision, and Fisher's exact tests on whether people reviewed, checked against records, or re-prompted before moving on.
- **3 · Decisions**: the reasoning given in each workflow (χ²), review time (AI output → decision) and deliberation time (previous decision → this one) compared with Mann–Whitney U and across reasonings with Kruskal–Wallis, what evidence each reasoning rested on, and a list of every decision.
- **4 · Sessions**: one number per session (length, AI turns, prompts, decisions, GATHER/JUDGE/STEER tasks, task variety, median review, …) with exact Mann–Whitney tests, so each person counts once.

The tab says how much weight the tests can bear with the number of sessions loaded. **Download CSVs** saves every table (`statistics-tables.csv`) and every coded row with its times, families and decision links (`coded-events.csv`) for R, SPSS or Excel.

## How columns are built

Consecutive rows of the same kind become one column: human tasks → `Human #n`, AI tasks → `AI #n`, handoffs → `Handoff #n`. Groups never cross a phase boundary.

## Exports

Each map tab exports as `<name>-visual.csv` (one hex color code per square, phase START/END markers above the headers, legend below) and `<name>-visual.png` for task types, plus `-task-families`, `-actions`, `-action-families` and `-all-levels` versions. In the all-levels CSV a tall square repeats its color on each row it covers. **Download all files** and **Download as .zip** also include the two statistics CSVs.

Open `index.html` directly in a browser to use it locally.

## Python version

The `python/` folder has a Python version of the earlier dashboard (`python app.py`), dark by default with a light/dark toggle, plus a command-line exporter. It still reads the older micro task / task type / macro task format (e.g. `examples/micro-example.csv`) and has no statistics tab. See `python/README.md`.
