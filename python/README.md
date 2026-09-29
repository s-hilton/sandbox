# Handoff Map (Python)

A Python version of the Workflow Map dashboard in `../index.html`. It reads the same transcript CSV/XLSX files, builds the same columns, and exports the same `<name>-visual.csv` and `<name>-visual.png` files.

## Setup

```bash
cd python
pip install -r requirements.txt
```

## Dashboard (Streamlit)

```bash
streamlit run app.py
```

- **Sidebar:** upload one or more `.csv` or `.xlsx` transcripts, turn the bundled example on or off, review parse notes, download everything as a zip, and look up the color key.
- **Main area:** one tab per workflow, plus an **All workflows** tab (tight first, then loose) once two or more are loaded. Each tab has its own CSV and PNG download buttons. Hover over a square to see its task or handoff type.

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
| `handoff_map/cli.py` | Batch export command |
| `app.py` | Streamlit dashboard |
| `tests/` | `pytest tests`: checks CSV output against files exported by the browser version |
