# Handoff Map (Python)

A Python version of the Workflow Map dashboard in `../index.html`. The page looks and works the same as the HTML version: an inputs panel on the left, one tab per workflow on the right, an **All workflows** tab, and a resizable split between them. Python reads the transcripts, builds the columns and makes every export (`<name>-visual.csv`, `<name>-visual.png`, `handoff-maps.zip`).

What's different from the HTML version:

- It opens in **dark mode**. The button in the bottom-right corner switches between light and dark, and your choice is remembered.
- **Hovering over a square** shows everything about it: the task or handoff type, whether it is a human task, AI task or handoff, the workflow, the step and the columns that step spans, the column and its position, where the square sits in that column, the agent (for a handoff, who it passes from and to), and its color code.

## Setup

```bash
cd python
pip install -r requirements.txt
```

## Dashboard

```bash
python app.py
```

This starts a local server at http://localhost:8501 and opens it in your browser. Use `--port` to pick another port, and `--no-browser` to skip opening a window. The server only listens on this computer.

## Run it in GitHub Codespaces

1. On the repository page, click **Code** → **Codespaces** → **Create codespace** on this branch.
2. Wait for it to finish setting up. The dashboard installs and starts by itself, and opens in a new browser tab.
3. If the tab doesn't open (for example, because of a pop-up blocker), open the **Ports** tab next to the terminal and click the globe icon next to **Handoff Map (8501)**.

To restart it later, run `cd python && python app.py --no-browser` in the terminal.

## Command line

```bash
python -m handoff_map transcript.csv other.xlsx -o out/        # one CSV + PNG per tab
python -m handoff_map *.csv -o out/ --zip                      # handoff-maps.zip
```

## Layout

| Path | What it holds |
| --- | --- |
| `handoff_map/core.py` | Color key, CSV/XLSX parsing, column grouping, CSV export |
| `handoff_map/render.py` | PNG export (Pillow) |
| `handoff_map/server.py` | Local web server behind the dashboard |
| `handoff_map/static/index.html` | The dashboard page (same markup and styles as `../index.html`) |
| `handoff_map/cli.py` | Batch export command |
| `app.py` | Starts the dashboard |
| `tests/` | `pytest tests`: checks output against files exported by the browser version |
