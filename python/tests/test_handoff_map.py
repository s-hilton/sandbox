import io
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from handoff_map.core import build_workflow, file_base, load_workflow, make_tabs, parse_csv, tab_csv, tab_levels  # noqa: E402
from handoff_map.render import tab_png  # noqa: E402

HERE = Path(__file__).resolve().parent
EXAMPLE = HERE.parents[1] / "examples" / "tight-example.csv"
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
    assert [x.name for x in high.columns[0].cells] == ["Black Box"]
    assert high.columns[0].cells[0].tasks == ["Black Box", "Black Box"]
    assert [(x.name, x.tasks) for x in high.columns[2].cells] == [
        ("Review AI", ["Cross-Checking Against AI Reasoning", "Pause"]), ("Prompting", ["Drafting Prompt"])]
    assert wf.columns[2].cells[1].group == "Review AI"
    # Same column structure, handoffs unchanged, task view untouched
    assert [c.label for c in high.columns] == [c.label for c in wf.columns]
    assert high.columns[1].cells == wf.columns[1].cells and len(wf.columns[0].cells) == 2
    # Shared names keep their task-type color; new higher-level names have their own
    approve = wf.columns[10].cells
    assert [(x.name, x.hex) for x in high.columns[10].cells] == [("Review AI", "#FFFFFF"), ("Decision Making", "#FFADBC")]
    assert [x.name for x in approve] == ["Reviewing AI Reasoning", "Approving"]
    assert high.columns[-1].cells[0].hex == "#FF7B00"  # Submitting Final Plan


def test_higher_level_header_and_new_column():
    rows = parse_csv("Loose,Task Type,Higher Level Task Type,Handoff Type,Agent\n"
                     ",Pause,,,Human\n,Approving,Decision Making,,Human\n,Pause,,,Human\n,,,General Request,\n"
                     ",Approving,,,Human\n")
    wf = build_workflow(rows, "l")
    assert wf.has_high and [c.label for c in wf.columns] == ["Human #1", "Handoff #1", "Human #2"]
    assert any("before the first higher-level" in w for w in wf.warnings)
    high = wf.at_level("high")
    assert [(x.name, x.tasks) for x in high.columns[0].cells] == [("Pause", ["Pause"]),
                                                                  ("Decision Making", ["Approving", "Pause"])]
    # A higher-level task carries on into the next column after a handoff
    assert [(x.name, x.hex) for x in high.columns[2].cells] == [("Decision Making", "#FFADBC")]


def test_exports_both_versions():
    tabs = make_tabs([load(EXAMPLE), load(HERE / "loose-example.csv", "loose")])
    names = [file_base(t) for tab in tabs for t in tab_levels(tab)]
    assert names == ["tight-example", "tight-example-high-level", "loose", "all-workflows",
                     "all-workflows-high-level"]
    high_csv = tab_csv(tab_levels(tabs[0])[1])
    assert "Decision Making,#FFADBC" in high_csv and "Approving" not in high_csv


def test_png_renders():
    tabs = make_tabs([load(EXAMPLE), load(HERE / "loose-example.csv")])
    img = Image.open(io.BytesIO(tab_png(tabs[-1])))
    assert img.format == "PNG" and img.width > 1000 and img.height > 400


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
        assert z.namelist() == ["all-workflows-visual.csv", "all-workflows-visual.png",
                                "all-workflows-high-level-visual.csv", "all-workflows-high-level-visual.png"]
        high = post("/api/export", {"kind": "csv", "tabs": [{**tab, "level": "high"}]}).decode()
        assert high == tab_csv(make_tabs([load(EXAMPLE), load(HERE / "loose-example.csv", "loose")])[-1].at_level("high"))
    finally:
        httpd.shutdown()
        httpd.server_close()
