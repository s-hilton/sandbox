"""Handoff Map dashboard (Streamlit). Run with: streamlit run app.py"""
from __future__ import annotations

import html
import io
import zipfile
from pathlib import Path

import streamlit as st

from handoff_map.core import (TYPE_GROUPS, Tab, Workflow, base_name, file_base, groups_of, legend_of,
                              load_workflow, make_tabs, tab_csv)
from handoff_map.render import tab_png

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "tight-example.csv"
KIND_TIP = {"human": "Human task", "ai": "AI task", "handoff": "Handoff"}
esc = lambda s: html.escape(str(s), quote=True)

CSS = """<style>
.hm{font:14px/1.45 "IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif}
.hm .sheet{overflow-x:auto;border:1px solid #dfe3e8;border-radius:8px;background:#fff;color:#1c232b;padding:14px}
.hm .stack{display:flex;flex-direction:column;gap:28px;width:max-content}
.hm .glabel{font:500 11px/1 ui-monospace,Menlo,monospace;letter-spacing:.08em;text-transform:uppercase;padding:4px 0 8px}
.hm .glabel.tight{color:#6b3fa0}.hm .glabel.loose{color:#1e7a6c}
.hm .btitle{font-weight:500;font-size:12.5px;margin-bottom:6px}
.hm table.viz{border-collapse:collapse;font:12px sans-serif;table-layout:fixed;margin:0}
.hm table.viz td,.hm table.viz th{border:1px solid #d9dde2;width:76px;min-width:76px;height:26px;padding:0;text-align:center;vertical-align:middle}
.hm table.viz th{font:500 11px ui-monospace,Menlo,monospace;color:#1c232b;background:#f3f5f7;white-space:nowrap}
.hm th.human{box-shadow:inset 0 -3px 0 #e0a15a}.hm th.ai{box-shadow:inset 0 -3px 0 #5a8fe0}.hm th.handoff{box-shadow:inset 0 -3px 0 #9aa5b1}
.hm td.stepcell{border:0!important;height:30px;padding:0 0 4px}
.hm .step{height:26px;margin:0 3px;border:1.5px solid #1c232b;border-bottom:0;display:flex;align-items:center;justify-content:space-between;gap:4px;padding:0 4px;font:500 11px sans-serif;overflow:hidden}
.hm .step .lbl{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.hm .step i{font:10px ui-monospace,monospace;font-style:normal;color:#5b6672}
.hm .sq{display:block;width:18px;height:18px;margin:auto;border-radius:2px;border:1px solid rgba(0,0,0,.14)}
.hm td.hit:hover{background:#e3eef6}
.hm td.hit:hover .sq{transform:scale(1.15);box-shadow:0 0 0 2px #fff,0 0 0 3.5px #1c232b}
.hm .unknown{background:repeating-linear-gradient(45deg,#fff 0 3px,#bbb 3px 5px)!important}
.hm .legend{display:flex;flex-wrap:wrap;gap:6px 16px}
.hm .key{display:flex;align-items:center;gap:8px;font-size:12.5px}
.hm .key code{font:11px ui-monospace,monospace;opacity:.7;background:none;padding:0}
.hm .sw{width:14px;height:14px;border-radius:2px;flex:none;border:1px solid rgba(0,0,0,.12)}
</style>"""


def table_html(f: Workflow) -> str:
    h = ['<table class="viz"><tbody>']
    if f.category == "tight" and f.steps:
        h.append("<tr>")
        c = 0
        for s in f.steps:
            if s.start > c:
                h.append(f'<td class="stepcell" colspan="{s.start - c}"></td>')
            tip = f"{s.label}: {f.columns[s.start].label} to {f.columns[s.end].label}"
            h.append(f'<td class="stepcell" colspan="{s.end - s.start + 1}" title="{esc(tip)}"><div class="step">'
                     f'<i>▸</i><span class="lbl">{esc(s.label)}</span><i>◂</i></div></td>')
            c = s.end + 1
        if c < len(f.columns):
            h.append(f'<td class="stepcell" colspan="{len(f.columns) - c}"></td>')
        h.append("</tr>")
    h.append("<tr>" + "".join(f'<th class="{c.kind}" scope="col">{c.label}</th>' for c in f.columns) + "</tr>")
    for r in range(f.rows_max):
        h.append("<tr>")
        for ci, col in enumerate(f.columns):
            if r >= len(col.cells):
                h.append("<td></td>")
                continue
            x, st_ = col.cells[r], f.step_for(ci)
            tip = "\n".join(filter(None, [
                x.name, f"{KIND_TIP[col.kind]} · {col.label} · item {r + 1} of {len(col.cells)}",
                st_.label if st_ else "", x.hex + ("" if x.known else " · no color set")]))
            h.append(f'<td class="hit" title="{esc(tip)}"><span class="sq{"" if x.known else " unknown"}" '
                     f'style="background:{x.hex}"></span></td>')
        h.append("</tr>")
    return "".join(h) + "</tbody></table>"


def legend_html(items) -> str:
    return '<div class="legend">' + "".join(
        f'<span class="key"><span class="sw{"" if x.known else " unknown"}" style="background:{x.hex}"></span>'
        f'{esc(x.name)} <code>{x.hex}</code></span>' for x in items) + "</div>"


@st.cache_data(show_spinner=False)
def load(filename: str, data: bytes, name: str) -> Workflow:
    return load_workflow(filename, data, name)


@st.cache_data(show_spinner=False)
def png_for(tab_key: str, _tab: Tab) -> bytes:
    return tab_png(_tab)


def tab_key(tab: Tab) -> str:
    return tab.id + ":" + ",".join(f.id for f in tab.files)


def zip_all(tabs: list[Tab]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for t in tabs:
            z.writestr(f"{file_base(t)}-visual.csv", tab_csv(t))
            z.writestr(f"{file_base(t)}-visual.png", png_for(tab_key(t), t))
    return buf.getvalue()


def render_tab(tab: Tab) -> None:
    files, f0, multi = tab.files, tab.files[0], tab.id == "all"
    head, dl = st.columns([4, 1], vertical_alignment="bottom")
    with head:
        st.caption("STACKED, TIGHT FIRST" if multi else f"{f0.category.upper()} WORKFLOW")
        stats = []
        if multi:
            stats += [f"**{sum(f.category == c for f in files)}** {c}" for c in ("tight", "loose")]
        stats += [f"**{sum(len(f.columns) for f in files)}** columns"]
        stats += [f"**{sum(f.counters[k] for f in files)}** {lbl}" for k, lbl in
                  (("human", "human"), ("ai", "AI"), ("handoff", "handoff"))]
        if not multi and f0.category == "tight":
            stats.append(f"**{len(f0.steps)}** steps")
        st.markdown(" · ".join(stats))
    with dl:
        base = file_base(tab)
        c1, c2 = st.columns(2)
        c1.download_button("CSV", tab_csv(tab), f"{base}-visual.csv", "text/csv", key=f"csv-{tab.id}")
        c2.download_button("PNG", png_for(tab_key(tab), tab), f"{base}-visual.png", "image/png", key=f"png-{tab.id}")

    if multi:
        body = '<div class="stack">' + "".join(
            f'<div><div class="glabel {cat}">{cat} · {len(fs)}</div><div class="stack">' +
            "".join(f'<div><div class="btitle">{esc(f.name)}</div>{table_html(f)}</div>' for f in fs) +
            "</div></div>" for cat, fs in groups_of(tab)) + "</div>"
    else:
        body = table_html(f0)
    st.html(f'{CSS}<div class="hm"><div class="sheet">{body}</div></div>')
    st.markdown("**Legend**")
    st.html(f'{CSS}<div class="hm">{legend_html(legend_of(files))}</div>')
    st.caption("Hover over a square to see its task or handoff type.")


def main() -> None:
    st.set_page_config(page_title="Handoff Map", layout="wide")

    with st.sidebar:
        st.title("Handoff Map")
        st.subheader("Upload transcripts")
        uploads = st.file_uploader(
            "Drop CSV files here", type=["csv", "xlsx"], accept_multiple_files=True,
            help="The first cell names the workflow category (Tight or Loose), followed by Task Type, "
                 "Handoff Type and Agent columns. Tight workflows list step labels down the first column.")
        show_example = st.toggle("Include the example transcript", value=EXAMPLE.exists(),
                                 disabled=not EXAMPLE.exists())

        sources = [("Example transcript.csv", EXAMPLE.read_bytes())] if show_example and EXAMPLE.exists() else []
        sources += [(u.name, u.getvalue()) for u in uploads or []]
        workflows, errors, names = [], [], set()
        for fname, data in sources:
            name, i = base_name(fname), 2
            while name in names:
                name, i = f"{base_name(fname)} ({i})", i + 1
            try:
                workflows.append(load(fname, data, name))
                names.add(name)
            except Exception as err:  # bad encodings, corrupt xlsx, empty files
                errors.append(f"{fname}: {err}")
        for e in errors:
            st.error(f"Could not read {e}.")

        st.subheader("Loaded workflows")
        if not workflows:
            st.caption("No workflows loaded yet.")
        for f in workflows:
            meta = (f"`{f.category.upper()}` {len(f.columns)} columns · {f.counters['human']} human · "
                    f"{f.counters['ai']} AI · {f.counters['handoff']} handoff")
            if f.category == "tight":
                meta += f" · {len(f.steps)} steps"
            with st.container(border=True):
                st.markdown(f"**{f.name}**  \n{meta}")
                for w in f.warnings:
                    st.warning(w, icon="⚠️")

        tabs = make_tabs(workflows)
        st.subheader("Download")
        st.caption("Each tab has its own CSV and PNG buttons. The CSV holds one column per group, with each "
                   "square stored as its hex color code.")
        if tabs:
            st.download_button(f"Download all {len(tabs) * 2} files as .zip", zip_all(tabs),
                               "handoff-maps.zip", "application/zip", type="primary")

        with st.expander(f"Color key · {sum(len(i) for _, i in TYPE_GROUPS)} task and handoff types"):
            for group, items in TYPE_GROUPS:
                st.caption(group.upper())
                st.html(CSS + '<div class="hm"><div class="legend" style="flex-direction:column;gap:4px">' + "".join(
                    f'<span class="key"><span class="sw" style="background:#{h}"></span>{esc(n)} <code>#{h}</code></span>'
                    for n, h in items) + "</div></div>")

    if not tabs:
        st.info("Upload a transcript CSV in the sidebar to see its handoff map here.")
        return
    labels = [("🟣 " if t.kind == "tight" else "🟢 " if t.kind == "loose" else "🔵 ") + t.title +
              (f" ({len(t.files)})" if t.id == "all" else "") for t in tabs]
    for t, container in zip(tabs, st.tabs(labels)):
        with container:
            render_tab(t)


main()
