import io
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from handoff_map.core import build_workflow, file_base, load_workflow, make_tabs, parse_csv, tab_csv, tab_levels  # noqa: E402
from handoff_map.render import tab_png  # noqa: E402

HERE = Path(__file__).resolve().parent
EXAMPLE = HERE.parents[1] / "examples" / "tight-example.csv"
MICRO = HERE.parents[1] / "examples" / "micro-example.csv"
GOLDEN = HERE / "golden"  # CSVs exported by the browser version (index.html)


def load(path, name=None):
    return load_workflow(path.name, path.read_bytes(), name)


def test_example_matches_browser_export():
    tab = make_tabs([load(EXAMPLE)])[0]
    assert tab_csv(tab) == (GOLDEN / "tight-example-visual.csv").read_bytes().decode()


def test_all_workflows_matches_browser_export():
    tabs = make_tabs([load(EXAMPLE), load(HERE / "loose-example.csv", "loose")])
    assert tabs[-1].id == "all"
    assert tab_csv(tabs[-1]) == (GOLDEN / "all-workflows-visual.csv").read_bytes().decode()


def test_example_structure():
    wf = load(EXAMPLE)
    assert wf.category == "tight"
    assert wf.counters == {"human": 7, "ai": 7, "handoff": 13}
    assert wf.steps[0].label == "Step 1: Propose" and len(wf.steps) == 5
    assert wf.columns[0].label == "AI #1" and wf.columns[0].cells[0].hex == "#FFB8FB"
    assert len(wf.warnings) == 1  # the Orienting to Next Step row with no higher-level type


def test_groups_never_cross_steps_and_agents_inherit():
    rows = parse_csv("Tight,Task Type,Handoff Type,Agent\nS1,Pause,,Human\n,Approving,,\nS2,Pause,,Human\n")
    wf = build_workflow(rows, "t")
    assert [c.label for c in wf.columns] == ["Human #1", "Human #2"]
    assert len(wf.columns[0].cells) == 2
    assert any("no agent" in w for w in wf.warnings)


def test_unknown_types_and_delimiter_sniffing():
    wf = build_workflow(parse_csv("Loose;Task Type;Handoff Type;Agent\n;Odd Thing;;AI\n"), "l")
    cell = wf.columns[0].cells[0]
    assert (cell.known, cell.hex) == (False, "#FFFFFF")
    assert any("Odd Thing" in w for w in wf.warnings)


def test_higher_level_task_types():
    wf = load(EXAMPLE)
    assert wf.has_high and not load(HERE / "loose-example.csv").has_high
    high = wf.at_level("high")
    # Blank higher-level cells continue the one above, so each higher-level task is one square
    assert [(x.name, len(x.tasks)) for x in high.columns[2].cells] == [("Validating the course plan", 17)]
    assert wf.columns[2].cells[6].group == "Validating the course plan"
    assert [(x.name, x.hex) for x in high.columns[18].cells] == [
        ("Evaluating the proposed schedule", "#FFF0AD"), ("Reviewing and refining course recommendations", "#ADFFD5")]
    # A blank row right after another agent's task has no higher-level type, so it keeps its task type
    assert [(x.name, x.tasks) for x in high.columns[22].cells] == [
        ("Orienting to Next Step", ["Orienting to Next Step"]),
        ("Decision Making", ["Reviewing AI Self-Check Results", "Approving"])]
    assert any("no macro task" in w for w in wf.warnings)
    # Same column structure, handoffs unchanged, task view untouched
    assert [c.label for c in high.columns] == [c.label for c in wf.columns]
    assert high.columns[1].cells == wf.columns[1].cells and len(wf.columns[2].cells) == 17
    # Shared names keep their task-type color
    assert high.columns[0].cells[0].hex == "#FFB8FB"  # Black Box


def test_higher_level_matches_browser_export():
    tabs = make_tabs([load(EXAMPLE), load(HERE / "loose-example.csv", "loose")])
    for tab, golden in ((tabs[0], "tight-example"), (tabs[-1], "all-workflows")):
        high = tab.at_level("high")
        assert file_base(high) == golden + "-macro"
        assert tab_csv(high) == (GOLDEN / f"{golden}-macro-visual.csv").read_bytes().decode()


def test_higher_level_header_and_new_column():
    rows = parse_csv("Loose,Task Type,Higher Level Task Type,Handoff Type,Agent\n"
                     ",Pause,,,Human\n,Approving,Decision Making,,Human\n,Pause,,,Human\n,,,General Request,\n"
                     ",Approving,,,Human\n")
    wf = build_workflow(rows, "l")
    assert wf.has_high and [c.label for c in wf.columns] == ["Human #1", "Handoff #1", "Human #2"]
    assert any("no macro task" in w for w in wf.warnings)
    high = wf.at_level("high")
    assert [(x.name, x.tasks) for x in high.columns[0].cells] == [("Pause", ["Pause"]),
                                                                  ("Decision Making", ["Approving", "Pause"])]
    # A higher-level task carries on into the next column after a handoff
    assert [(x.name, x.hex) for x in high.columns[2].cells] == [("Decision Making", "#FFADBC")]


def test_exports_both_versions():
    tabs = make_tabs([load(EXAMPLE), load(HERE / "loose-example.csv", "loose")])
    names = [file_base(t) for tab in tabs for t in tab_levels(tab)]
    assert names == ["tight-example", "tight-example-macro", "tight-example-all-levels", "loose",
                     "all-workflows", "all-workflows-macro", "all-workflows-all-levels"]


def test_micro_tasks():
    wf = load(MICRO)
    assert wf.levels == ["micro", "task", "high"] and wf.counters == {"human": 4, "ai": 4, "handoff": 7}
    human = wf.columns[2]
    # A row with only a micro task belongs to the task type above it
    assert [(x.name, x.tasks) for x in human.cells[:2]] == [
        ("Consulting Degree Progress Record", ["SCROLL_REFERENCE_DOC", "HOVER_REFERENCE_DOC"]),
        ("Cross-Checking Against Degree Progress", ["SCROLL_REFERENCE_DOC", "CURSOR_TRANSIT"])]
    micro = wf.at_level("micro").columns[2].cells
    assert len(micro) == 25 and (micro[0].name, micro[0].hex, micro[0].group) == (
        "SCROLL_REFERENCE_DOC", "#40FFBF", "Consulting Degree Progress Record")
    assert [(x.name, x.rows) for x in human.high_cells] == [("Validating the course plan", 25)]
    # A micro task with no task type above it stands in for its own task type
    assert wf.columns[0].cells[0].name == "SESSION_START" and len(wf.warnings) == 1
    # Every micro, task and macro name in the example has a color
    assert all(x.known for lv in wf.levels for c in wf.at_level(lv).columns for x in c.cells)


def test_all_levels_view():
    wf = load(MICRO).at_level("all")
    assert [(c.label, c.sub) for c in wf.columns[:5]] == [
        ("AI #1", "micro"), ("AI #1", "task"), ("AI #1", "high"), ("Handoff #1", ""), ("Human #1", "micro")]
    task, macro = wf.columns[5].cells, wf.columns[6].cells
    assert len(task) == len(macro) == 25  # one row per micro task
    assert task[0].rows == 2 and task[1] is None and task[2].name == "Cross-Checking Against Degree Progress"
    assert macro[0].rows == 25 and all(x is None for x in macro[1:])
    # A file without micro tasks shows task types next to macro tasks
    assert [c.sub for c in load(EXAMPLE).at_level("all").columns[:3]] == ["task", "high", ""]


def test_micro_example_matches_browser_export():
    tab = make_tabs([load(MICRO)])[0]
    for t in tab_levels(tab):
        assert tab_csv(t) == (GOLDEN / f"{file_base(t)}-visual.csv").read_bytes().decode()
    assert [file_base(t) for t in tab_levels(tab)] == [
        "micro-example", "micro-example-micro", "micro-example-macro", "micro-example-all-levels"]


def test_png_renders():
    tabs = make_tabs([load(EXAMPLE), load(HERE / "loose-example.csv")])
    img = Image.open(io.BytesIO(tab_png(tabs[-1])))
    assert img.format == "PNG" and img.width > 1000 and img.height > 400
    img = Image.open(io.BytesIO(tab_png(make_tabs([load(MICRO)])[0].at_level("all"))))
    assert img.format == "PNG" and img.height > 600


def test_dashboard_server_round_trip():
    import base64
    import json
    import threading
    import urllib.request
    import zipfile
    from http.server import ThreadingHTTPServer

    from handoff_map.server import Handler

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{httpd.server_port}"

    def post(path, body):
        req = urllib.request.Request(url + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
        return urllib.request.urlopen(req).read()

    try:
        page = urllib.request.urlopen(url + "/").read().decode()
        assert 'data-theme="dark"' in page and 'id="theme-toggle"' in page
        files = [{"name": n, "filename": p.name, "data": base64.b64encode(p.read_bytes()).decode()}
                 for n, p in (("tight-example", EXAMPLE), ("loose", HERE / "loose-example.csv"))]
        wfs = json.loads(post("/api/parse", {"files": files}))["workflows"]
        assert [w["name"] for w in wfs] == ["tight-example", "loose"]
        tab = {"id": "all", "title": "All workflows", "kind": "all", "files": wfs}
        csv_bytes = post("/api/export", {"kind": "csv", "tabs": [tab]})
        assert csv_bytes == (GOLDEN / "all-workflows-visual.csv").read_bytes()
        z = zipfile.ZipFile(io.BytesIO(post("/api/export", {"kind": "zip", "tabs": [tab]})))
        assert z.namelist() == [f"all-workflows{v}-visual.{x}" for v in ("", "-macro", "-all-levels") for x in ("csv", "png")]
        high = post("/api/export", {"kind": "csv", "tabs": [{**tab, "level": "high"}]}).decode()
        assert high == tab_csv(make_tabs([load(EXAMPLE), load(HERE / "loose-example.csv", "loose")])[-1].at_level("high"))
    finally:
        httpd.shutdown()
        httpd.server_close()
