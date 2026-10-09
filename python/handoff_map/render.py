"""PNG export with Pillow, laid out like the browser dashboard's canvas export."""
from __future__ import annotations

import io
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from .core import LEVEL_NAME, Cell, Tab, Workflow, groups_of, legend_of

P = dict(col=76, row=26, sq=18, head=28, step=32, title=22, group=24, pad=24, gap_block=28, gap_group=56)
SCALE = 2
INK, MUTED, FAINT, HEAD_BG, GRID = "#1c232b", "#5b6672", "#7a8591", "#f3f5f7", "#d9dde2"
KIND = {"human": "#e0a15a", "ai": "#5a8fe0", "handoff": "#9aa5b1"}
CAT = {"tight": "#6b3fa0", "loose": "#1e7a6c"}

_FONT_FILES = {
    "sans": ["DejaVuSans.ttf", "LiberationSans-Regular.ttf", "Arial.ttf", "arial.ttf", "Helvetica.ttc"],
    "sans-bold": ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf", "Helvetica.ttc"],
    "mono": ["DejaVuSansMono.ttf", "LiberationMono-Regular.ttf", "Menlo.ttc", "consola.ttf", "Courier New.ttf"],
}
_FONT_DIRS = ["", "/usr/share/fonts/truetype/dejavu/", "/usr/share/fonts/truetype/liberation/",
              "/System/Library/Fonts/", "/Library/Fonts/", "C:/Windows/Fonts/"]


@lru_cache(maxsize=None)
def font(kind: str, size: float) -> ImageFont.ImageFont:
    px = round(size * SCALE)
    for name in _FONT_FILES[kind]:
        for d in _FONT_DIRS:
            try:
                return ImageFont.truetype(d + name, px)
            except OSError:
                continue
    return ImageFont.load_default(px)


def _fit(draw: ImageDraw.ImageDraw, text: str, fnt, max_w: float) -> str:
    if draw.textlength(text, font=fnt) <= max_w * SCALE:
        return text
    while len(text) > 1 and draw.textlength(text + "…", font=fnt) > max_w * SCALE:
        text = text[:-1]
    return text + "…"


def _measure(f: Workflow) -> tuple[int, int]:
    return max(1, len(f.columns)) * P["col"], (P["step"] if f.category == "tight" else 0) + P["head"] + f.rows_max * P["row"]


def tab_png(tab: Tab) -> bytes:
    """Render one tab as PNG bytes (2x scale, white background)."""
    multi = tab.id == "all"
    groups = groups_of(tab)
    legend = legend_of(tab.files)

    # Layout, in CSS pixels; every draw call multiplies by SCALE
    placed, group_y = [], []
    y = P["pad"] + 30 if multi else P["pad"] + 26
    max_w = max([P["col"]] + [_measure(f)[0] for f in tab.files])
    for gi, (_, files) in enumerate(groups):
        if gi:
            y += P["gap_group"] - P["gap_block"]
        if multi:
            group_y.append(y)
            y += P["group"]
        for f in files:
            ty = None
            if multi:
                ty = y + P["title"] / 2 - 2
                y += P["title"]
            placed.append((f, P["pad"], y, ty))
            y += _measure(f)[1] + P["gap_block"]
    grid_end = y - P["gap_block"]

    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    item_w = max([120] + [probe.textlength(f"{l.name}  {l.hex}", font=font("sans", 12)) / SCALE for l in legend]) + 30
    W = max(P["pad"] + max_w + P["pad"], 520)
    per_row = max(1, int((W - 2 * P["pad"]) // item_w))
    legend_top = grid_end + 28
    H = legend_top + 22 + -(-len(legend) // per_row) * 20 + P["pad"]

    img = Image.new("RGB", (round(W * SCALE), round(H * SCALE)), "#ffffff")
    d = ImageDraw.Draw(img)
    s = lambda v: round(v * SCALE)

    def text(x, y, t, fnt, fill, anchor="lm"):
        d.text((s(x), s(y)), t, font=fnt, fill=fill, anchor=anchor)

    def rect(x, y, w, h, fill):
        d.rectangle([s(x), s(y), s(x + w) - 1, s(y + h) - 1], fill=fill)

    def line(x1, y1, x2, y2, fill, width=1.0):
        d.line([(s(x1), s(y1)), (s(x2), s(y2))], fill=fill, width=max(1, round(width * SCALE)))

    def swatch(x, y, size, cell: Cell, height=None):
        height = height or size
        box = [s(x), s(y), s(x + size) - 1, s(y + height) - 1]
        if cell.known:
            d.rectangle(box, fill=cell.hex)
        else:
            tile = Image.new("RGB", (s(size), s(height)), "#ffffff")
            td = ImageDraw.Draw(tile)
            for k in range(-round(height), size, 5):
                td.line([(s(k), s(height)), (s(k + height), 0)], fill="#bbbbbb", width=s(2))
            img.paste(tile, (s(x), s(y)))
        d.rectangle(box, outline="#d1d1d1", width=1)

    # Heading
    heading = "All workflows" if multi else tab.title
    sub = (f"{len(tab.files)} workflows · stacked, tight first" if multi
           else f"{tab.files[0].category.upper()} WORKFLOW")
    sub += {"micro": " · MICRO TASKS", "high": " · MACRO TASKS", "all": " · MICRO, TASK AND MACRO"}.get(tab.level, "")
    text(P["pad"], P["pad"] + 8, heading, font("sans-bold", 16), INK)
    tw = d.textlength(heading, font=font("sans-bold", 16)) / SCALE
    text(P["pad"] + tw + 12, P["pad"] + 9, sub, font("mono", 11), MUTED)

    if multi:
        for (cat, files), gy in zip(groups, group_y):
            text(P["pad"], gy + 6, f"{cat.upper()} · {len(files)}", font("mono", 11), CAT[cat])
            rect(P["pad"], gy + 14, max_w, 1.5, CAT[cat])

    for f, bx, by, ty in placed:
        if multi:
            text(bx, ty, _fit(d, f.name, font("sans-bold", 12), max_w), font("sans-bold", 12), INK)
        y = by
        if f.category == "tight":
            for st in f.steps:
                sx, sw = bx + st.start * P["col"] + 3, (st.end - st.start + 1) * P["col"] - 6
                pts = [(sx, y + P["step"] - 2), (sx, y + 3), (sx + sw, y + 3), (sx + sw, y + P["step"] - 2)]
                d.line([(s(px), s(py)) for px, py in pts], fill=INK, width=s(1.5))
                text(sx + 4, y + 16, "▸", font("mono", 10), MUTED, "lm")
                text(sx + sw - 4, y + 16, "◂", font("mono", 10), MUTED, "rm")
                text(sx + sw / 2, y + 16, _fit(d, st.label, font("sans-bold", 11), sw - 28), font("sans-bold", 11), INK, "mm")
            y += P["step"]
        for i, col in enumerate(f.columns):
            cx = bx + i * P["col"]
            rect(cx, y, P["col"], P["head"], HEAD_BG)
            rect(cx, y + P["head"] - 3, P["col"], 3, KIND[col.kind])
            if col.sub:  # all-levels view: column on top, level below
                text(cx + P["col"] / 2, y + 8, col.label, font("mono", 9), MUTED, "mm")
                text(cx + P["col"] / 2, y + 18, LEVEL_NAME[col.sub], font("sans-bold", 10), INK, "mm")
            else:
                text(cx + P["col"] / 2, y + P["head"] / 2 - 1, col.label, font("mono", 11), INK, "mm")
        for r in range(f.rows_max):
            for i, col in enumerate(f.columns):
                x = col.cells[r] if r < len(col.cells) else None
                if x:  # a square spanning several rows (all-levels view) is drawn tall
                    swatch(bx + i * P["col"] + (P["col"] - P["sq"]) / 2,
                           y + P["head"] + r * P["row"] + (P["row"] - P["sq"]) / 2, P["sq"], x,
                           P["sq"] + (x.rows - 1) * P["row"] if col.sub else None)
        w, h = len(f.columns) * P["col"], P["head"] + f.rows_max * P["row"]
        for i in range(len(f.columns) + 1):
            line(bx + i * P["col"], y, bx + i * P["col"], y + h, GRID)
        for r in range(f.rows_max + 2):
            ly = y if r == 0 else y + P["head"] + (r - 1) * P["row"]
            line(bx, ly, bx + w, ly, GRID)

    text(P["pad"], legend_top + 6, "LEGEND", font("mono", 11), MUTED)
    for i, l in enumerate(legend):
        lx, ly = P["pad"] + (i % per_row) * item_w, legend_top + 22 + (i // per_row) * 20
        swatch(lx, ly, 13, l)
        text(lx + 19, ly + 7, l.name, font("sans", 12), INK)
        nw = d.textlength(l.name, font=font("sans", 12)) / SCALE
        text(lx + 25 + nw, ly + 7, l.hex, font("mono", 11), FAINT)

    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()
