#!/usr/bin/env python3
"""Render a data table as a PNG in the same look as the charts (brand.py): a white sheet in a thin ink frame, IBM Plex type
(fonts in ./fonts), figures in Plex Mono, one cobalt accent, a title block bottom right and the dated source line bottom left.

A table is written as a small dict rather than as HTML, so the tables stay diffable and the style lives in one place. Usage:

    python3 table.py spec.json out.png          one table
    python3 table.py specs.json outdir/         a list of tables, named by their "slug"
    python3 table.py --selftest

Spec keys: title, subtitle, columns (list of {head, sub?, align?}), rows (list of lists of cells),
where a cell is a string or {text, sub?, pill?, pill_text?, pill_pos?, mono?}, pill is
green|amber|red|grey|accent and pill_pos is before (the default) or after; plus optional band rows
({band: "..."}), legend, source, source_date, width, day (ISO date for the sheet number, default
today) and signature (default true; false drops the title block).

Rendering is Chrome via Playwright at deviceScaleFactor 2. If Playwright is missing the script says so and writes the HTML
beside the target, so the page can be shot by hand rather than the run failing silently.
Run: uv run --with playwright python scripts/charts/table.py data/tables.json plots/   (once: uv run --with playwright playwright install chromium)
"""
import argparse
import html
import json
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

FONTS = Path(__file__).resolve().parent / "fonts"

PALETTE = {  # brand.py: INK, MUTED, GRID, ACCENT, WARN
    "ink": "#111418",
    "mid": "#5B6470",
    "faint": "#8A93A0",
    "rule": "#E6E8EB",
    "rule_head": "#111418",
    "band": "#F1F3F5",
    "green_bg": "#E3F1E7", "green_ink": "#1F6B3A",
    "amber_bg": "#FBF1DC", "amber_ink": "#8A5A00",
    "red_bg": "#F8E4E2", "red_ink": "#B3261E",
    "grey_bg": "#ECEEF1", "grey_ink": "#5B6470",
    "accent_bg": "#E6EAFB", "accent_ink": "#2440D6",
}
PILLS = ("green", "amber", "red", "grey", "accent")

FACES = [("Plex Sans", "IBMPlexSans-Regular", 400), ("Plex Sans", "IBMPlexSans-SemiBold", 600),
         ("Plex Sans", "IBMPlexSans-Bold", 700), ("Plex Cond", "IBMPlexSansCondensed-Bold", 700),
         ("Plex Mono", "IBMPlexMono-Regular", 400), ("Plex Mono", "IBMPlexMono-SemiBold", 600)]

CSS = """
* { box-sizing: border-box; }
body { margin: 0; background: #fff; font-family: "Plex Sans", Helvetica, Arial, sans-serif;
       color: %(ink)s; -webkit-font-smoothing: antialiased; }
.sheet { width: %(width)spx; padding: 18px; background: #fff; }
.wrap { border: 1.5px solid %(ink)s; padding: 38px 44px 22px; }
h1 { font-family: "Plex Cond", "Plex Sans", sans-serif; font-size: 30px; line-height: 1.12; font-weight: 700;
     margin: 0; max-width: 88%%; }
.sub { font-family: "Plex Mono", monospace; font-size: 13px; letter-spacing: 1.2px; text-transform: uppercase;
       color: %(mid)s; margin-top: 10px; }
table { width: 100%%; border-collapse: collapse; margin-top: 28px; }
th { font-family: "Plex Mono", monospace; font-size: 11.5px; font-weight: 400; letter-spacing: 1px;
     text-transform: uppercase; color: %(mid)s; text-align: left; padding: 0 16px 9px 0; vertical-align: bottom; }
th .s { display: block; font-size: 10.5px; letter-spacing: .6px; color: %(faint)s; margin-top: 3px; }
thead tr { border-bottom: 1.5px solid %(rule_head)s; }
td { font-size: 15px; line-height: 1.5; padding: 13px 16px 13px 0; vertical-align: top;
     border-bottom: 1px solid %(rule)s; }
td:last-child, th:last-child { padding-right: 0; }
tr.band td { background: %(band)s; font-family: "Plex Mono", monospace; font-size: 12px; letter-spacing: 1px;
             text-transform: uppercase; color: %(ink)s; padding: 9px 12px; border-bottom: none; }
td.lab { font-weight: 600; color: %(ink)s; }
td .s { display: block; font-size: 13px; font-weight: 400; color: %(mid)s; margin-top: 3px; }
td .mono { font-family: "Plex Mono", monospace; font-size: 14.5px; font-weight: 600; }
.r { text-align: right; }
.pill { display: inline-block; font-family: "Plex Mono", monospace; font-size: 11.5px; font-weight: 600;
        letter-spacing: .4px; line-height: 1; padding: 5px 8px; border-radius: 2px; margin-bottom: 5px; }
.legend { font-size: 12.5px; line-height: 1.55; color: %(mid)s; margin-top: 18px; max-width: 78%%; }
.foot { display: flex; justify-content: space-between; align-items: flex-end; gap: 24px; margin-top: 26px; }
.src { font-family: "Plex Mono", monospace; font-size: 11px; line-height: 1.5; color: %(mid)s; flex: 1; }
.tb { display: flex; border: 1.5px solid %(ink)s; font-family: "Plex Mono", monospace; flex: none; }
.tb div { padding: 7px 12px 6px; min-width: 128px; }
.tb div + div { border-left: 1px solid %(ink)s; }
.tb b { display: block; font-size: 12px; font-weight: 600; color: %(ink)s; }
.tb span { display: block; font-size: 11px; color: %(mid)s; margin-top: 2px; }
"""


def _fontfaces():
    """@font-face rules for the brand's static Plex files; missing files fall back to system fonts."""
    rules = []
    for fam, f, w in FACES:
        path = FONTS / f"{f}.ttf"
        if path.exists():
            rules.append(f'@font-face {{ font-family: "{fam}"; src: url("file://{path}"); font-weight: {w}; }}')
    return "\n".join(rules)


def _title_block(day):
    y, wk, _ = day.isocalendar()
    cells = (("JULIEN SIMON", "@julsimon"), (f"SHEET {y}-{wk:02d}", day.strftime("%d %b %Y").upper()),
             ("AI REALIST", "airealist.ai"))
    return '<div class="tb">' + "".join(f"<div><b>{a}</b><span>{b}</span></div>" for a, b in cells) + "</div>"


def _cell(c, align=""):
    """A cell is a string, or a dict with text, an optional sub-line, a pill and a mono flag."""
    if not isinstance(c, dict):
        c = {"text": str(c)}
    pill = ""
    if c.get("pill"):
        k = c["pill"]
        if k not in PILLS:
            raise ValueError(f"unknown pill {k!r}")
        if c.get("pill_text"):
            pill = (f'<span class="pill" style="background:{PALETTE[k + "_bg"]};color:{PALETTE[k + "_ink"]}">'
                    f'{html.escape(c["pill_text"])}</span>')
    txt = html.escape(c.get("text", ""))
    if c.get("mono"):
        txt = f'<span class="mono">{txt}</span>'
    # verdict first when the cell is prose; value first when it is a
    # number, because a pill above "$0.25" reads as the headline and the number as the caption
    out = (pill + "<br>" + txt) if (pill and c.get("pill_pos", "before") == "before") else txt
    if pill and c.get("pill_pos", "before") == "after":
        out += '<span class="s" style="margin-top:6px">' + pill + "</span>"
    if c.get("sub"):
        out += f'<span class="s">{html.escape(c["sub"])}</span>'
    cls = " ".join(x for x in [c.get("cls", ""), align] if x)
    return f'<td class="{cls}">{out}</td>'


def build_html(spec):
    width = int(spec.get("width", 1200))
    css = _fontfaces() + CSS % dict(PALETTE, width=width)
    cols = spec["columns"]
    head = "".join(
        f'<th class="{c.get("align", "")}">{html.escape(c["head"])}'
        + (f'<span class="s">{html.escape(c["sub"])}</span>' if c.get("sub") else "")
        + "</th>"
        for c in cols)
    body = []
    for row in spec["rows"]:
        if isinstance(row, dict) and "band" in row:
            body.append(f'<tr class="band"><td colspan="{len(cols)}">{html.escape(row["band"])}</td></tr>')
            continue
        if len(row) != len(cols):
            raise ValueError(f"row has {len(row)} cells against {len(cols)} columns: {row}")
        cells = [_cell(c, cols[i].get("align", "")) for i, c in enumerate(row)]
        if not isinstance(row[0], dict) or not row[0].get("pill"):
            cells[0] = cells[0].replace('<td class="', '<td class="lab ', 1)
        body.append("<tr>" + "".join(cells) + "</tr>")
    legend = f'<div class="legend">{html.escape(spec["legend"])}</div>' if spec.get("legend") else ""
    src = spec.get("source", "Source: The AI Realist, airealist.ai")
    if spec.get("source_date"):
        src += ", " + spec["source_date"]
    day = date.fromisoformat(spec["day"]) if spec.get("day") else date.today()
    block = _title_block(day) if spec.get("signature", True) else ""
    return f"""<!doctype html><meta charset="utf-8"><style>{css}</style>
<div class="sheet"><div class="wrap">
  <h1>{html.escape(spec["title"])}</h1>
  {'<div class="sub">' + html.escape(spec["subtitle"]) + "</div>" if spec.get("subtitle") else ""}
  <table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>
  {legend}
  <div class="foot"><div class="src">{html.escape(src)}</div>{block}</div>
</div></div>"""


def render(spec, out):
    """Write the PNG. Chrome at 2x, because a table is type and type wants a browser."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    page = out.with_suffix(".html")
    page.write_text(build_html(spec), encoding="utf-8")
    script = f"""
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(device_scale_factor=2, viewport={{"width": {int(spec.get('width', 1200))}, "height": 900}})
    pg.goto("file://{page.resolve()}")
    pg.wait_for_timeout(250)
    pg.locator(".sheet").screenshot(path="{out.resolve()}")
    b.close()
"""
    for exe in (Path(".venv/bin/python"), Path(sys.executable)):
        if not exe.exists():
            continue
        r = subprocess.run([str(exe), "-c", script], capture_output=True, text=True)
        if r.returncode == 0 and out.exists():
            page.unlink(missing_ok=True)
            return True
        err = r.stderr.strip().splitlines()[-1] if r.stderr.strip() else ""
    print(f"could not render with Playwright ({err}); HTML kept at {page} to shoot by hand")
    return False


def selftest():
    spec = {
        "title": "A title", "subtitle": "A subtitle",
        "columns": [{"head": "Left"}, {"head": "Mid", "sub": "with a sub"}, {"head": "Right", "align": "r"}],
        "rows": [["a", {"text": "b", "sub": "under"}, "c"],
                 {"band": "A band"},
                 ["d", {"text": "e", "pill": "green", "pill_text": "Solved"}, {"text": "f", "mono": True}]],
        "legend": "Green means solved.", "source_date": "September 2026",
    }
    h = build_html(spec)
    assert "A title" in h and "A subtitle" in h and 'class="band"' in h, "structure"
    assert PALETTE["green_bg"] in h and "Solved" in h, "pill"
    assert '<span class="mono">f</span>' in h, "mono"
    assert 'class="lab ' in h, "first column is a label"
    assert h.count("<tr>") == 3 and h.count('<tr class="band">') == 1, "row count"
    try:
        build_html({**spec, "rows": [["only", "two"]]})
        raise AssertionError("a short row must be refused")
    except ValueError:
        pass
    try:
        build_html({**spec, "rows": [["a", {"text": "b", "pill": "purple", "pill_text": "x"}, "c"]]})
        raise AssertionError("an unknown pill must be refused")
    except ValueError:
        pass
    assert "SHEET " in h and "AI REALIST" in h, "title block on by default"
    assert "SHEET " not in build_html({**spec, "signature": False}), "signature: false drops it"
    assert 'class="tb"' in build_html({**spec, "day": "2026-09-27"}) and "SHEET 2026-39" in build_html({**spec, "day": "2026-09-27"}), "sheet number from day"
    assert "&lt;script&gt;" in build_html({**spec, "title": "<script>"}), "titles are escaped"
    print("ok: html builds, pills and bands render, short rows and unknown pills are refused, title block and sheet number, text is escaped")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", nargs="?")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return 0 if selftest() else 1
    if not a.spec or not a.out:
        ap.print_help()
        return 0
    data = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    specs = data if isinstance(data, list) else [data]
    ok = True
    for s in specs:
        out = Path(a.out) / f"{s['slug']}.png" if len(specs) > 1 or Path(a.out).is_dir() else Path(a.out)
        ok = render(s, out) and ok
        print(("wrote " if out.exists() else "failed ") + str(out))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
