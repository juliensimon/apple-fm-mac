#!/usr/bin/env python3
"""The runtime diagram of the piece: which models one request touches on a Mac, in which process, on which unit.
Datasheet look, from the editorial table renderer (fonts, palette, title block), drawn as inline SVG and shot by Chrome.
Every box is something the system log, the file-read trace or the power meter showed on 2026-10-24 (REPORT 1, 2, 5, 6,
21, 22, 28); dashed boxes and arrows are inferences or off-device paths. No model file was read.
Run: uv run --with playwright python scripts/charts/make_runtime_diagram.py [out.png]"""
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import table  # noqa: E402  (fonts, palette, title block, Chrome shot)

P = table.PALETTE
INK, MID, FAINT, RULE, ACC, ACC_BG = P["ink"], P["mid"], P["faint"], P["rule"], P["accent_ink"], P["accent_bg"]
W, H = 1160, 760


def box(x, y, w, h, title, lines=(), dashed=False, fill="#fff", accent=False, tag=None):
    st = f'stroke="{ACC if accent else INK}" stroke-width="{1.6 if accent else 1.2}"' + (' stroke-dasharray="5 4"' if dashed else "")
    s = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" {st}/>',
         f'<text x="{x + 12}" y="{y + 22}" class="bt">{title}</text>']
    for i, l in enumerate(lines):
        s.append(f'<text x="{x + 12}" y="{y + 42 + i * 17}" class="bl">{l}</text>')
    if tag:
        s.append(f'<text x="{x + w - 10}" y="{y + 20}" class="tag" text-anchor="end">{tag}</text>')
    return "\n".join(s)


def arrow(x1, y1, x2, y2, label="", dashed=False, lx=None, ly=None, anchor="middle"):
    d = ' stroke-dasharray="5 4"' if dashed else ""
    s = f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{INK}" stroke-width="1.3" marker-end="url(#ah)"{d}/>'
    if label:
        s += f'<text x="{lx if lx is not None else (x1 + x2) / 2}" y="{ly if ly is not None else (y1 + y2) / 2 - 6}" class="al" text-anchor="{anchor}">{label}</text>'
    return s


def svg():
    g = []
    # row 1: the caller, the framework, the daemon
    g.append(box(20, 20, 220, 74, "Your app or script", ["Swift framework, fm, fm serve"]))
    g.append(arrow(240, 57, 330, 57, "XPC"))
    g.append(box(330, 20, 330, 74, "modelmanagerd (system service)", ["opens sessions, keeps the memory budget"], tag="LOG"))
    g.append(arrow(660, 57, 830, 57, "harder requests", dashed=True))
    g.append(box(830, 20, 310, 74, "Private Cloud Compute", ["Apple's server models; an app must", "choose this model itself"], dashed=True, tag="APPLE"))
    # the two provider processes
    g.append(f'<text x="380" y="132" class="cap">TWO MODEL PROCESSES, OWNED BY A SYSTEM USER</text>')
    # safety process (left)
    g.append(f'<rect x="20" y="142" width="330" height="470" fill="{P["band"]}" stroke="{INK}" stroke-width="1.2"/>')
    g.append(f'<text x="34" y="166" class="pt">Safety models and checks</text><text x="336" y="166" class="pm" text-anchor="end">0.7 GiB</text>')
    g.append(box(36, 182, 298, 58, "Text sanitizer", ["screens the prompt first"], tag="LOG"))
    g.append(box(36, 252, 298, 76, "Safety classifier, 300M", ["checks the request; refused 4 of", "my 300 test questions"], tag="LOG"))
    g.append(box(36, 340, 298, 58, "Multimodal guard, 300M", ["checks images"], tag="LOG"))
    g.append(box(36, 410, 298, 76, "Output checks", ["a deny-list of tokens and an", "output safety configuration"], tag="LOG"))
    g.append(box(36, 498, 298, 98, "Own tokenizer", ["a second, smaller vocabulary file:", "the safety models do not share", "the main model's tokenizer"], tag="LOG"))
    # main process (right)
    g.append(f'<rect x="380" y="142" width="760" height="470" fill="#fff" stroke="{INK}" stroke-width="1.2"/>')
    g.append(f'<text x="394" y="166" class="pt">Main process: Core Advanced</text><text x="1126" y="166" class="pm" text-anchor="end">1.3 GiB</text>')
    g.append(box(396, 182, 220, 76, "Tokenizer", ["Gemma 3's vocabulary,", "262,144 entries"], tag="MEASURED"))
    g.append(box(632, 182, 238, 76, "Use-case adapter", ["fm_api_generic for the public API;", "28.7 MiB of changeable weights"], tag="LOG"))
    g.append(box(886, 182, 238, 76, "Image encoder", ["turns an image into tokens"], tag="LOG"))
    g.append(box(396, 274, 300, 94, "Dense block: the router", ["reads the prompt, picks a fixed", "set of experts, picks again", "about every 32 tokens"], accent=True, fill=ACC_BG, tag="APPLE + TRACE"))
    g.append(box(396, 384, 300, 94, "Always-loaded weights", ["636 MiB of model pages, at most", "2.7B weights at 2 bits. Assumption:", "Apple's 'shared experts'"], tag="LOG + ASSUMPTION"))
    g.append(box(724, 274, 400, 94, "Expert cache", ["holds the routed experts a prompt picked;", "new ones come in as 294,912-byte blocks,", "43 to 64 MiB for a new subject"], accent=True, fill=ACC_BG, tag="TRACE"))
    g.append(box(724, 384, 400, 94, "Draft model", ["about 9 MiB of pages; guesses a few", "tokens ahead for the main model to check", "(speculative decoding)"], dashed=True, tag="LOG + ASSUMPTION"))
    g.append(box(396, 494, 728, 102, "The Neural Engine runs the main model", ["4.2 W reading a prompt, 3.8 W writing; the GPU stays idle at 65 mW", "attention cache: 35 MiB at a 512-token window, 560 MiB at 8,192", "programs compiled ahead of time for this chip family"], tag="POWER + LOG"))
    # flash store below the main process
    g.append(f'<rect x="724" y="650" width="400" height="74" fill="#fff" stroke="{ACC}" stroke-width="1.6"/>')
    g.append(f'<text x="736" y="672" class="bt">Flash storage (SSD)</text>')
    g.append(f'<text x="736" y="692" class="bl">ifp_rasterized_weights.bin, 4.95 GB:</text>')
    g.append(f'<text x="736" y="709" class="bl">the full 20 billion parameters stay here</text>')
    g.append(f'<text x="1114" y="670" class="tag" text-anchor="end">TRACE</text>')
    g.append(f'<polyline points="1132,650 1132,330 1128,330" fill="none" stroke="{INK}" stroke-width="1.3" marker-end="url(#ah)"/>')
    g.append(f'<text x="1122" y="640" class="al" text-anchor="end">reads on demand</text>')
    # links inside the main process and between processes
    g.append(arrow(696, 321, 724, 321, ""))
    g.append(arrow(60, 94, 60, 142, "1 check the prompt", lx=70, ly=122, anchor="start"))
    g.append(arrow(334, 290, 396, 300, "", ))
    g.append(f'<text x="365" y="284" class="al" text-anchor="middle">2</text>')
    g.append(arrow(396, 452, 334, 448, ""))
    g.append(f'<text x="365" y="440" class="al" text-anchor="middle">3</text>')
    g.append('<text x="20" y="642" class="leg">1 the request is screened, 2 the main model writes, 3 the answer is checked.</text>')
    g.append('<text x="20" y="660" class="leg">The log names the sanitizer and the output checks, not the process that runs them.</text>')
    g.append(f'<text x="20" y="684" class="leg">Solid: seen on the Mac (LOG system log, TRACE file reads, POWER power meter, MEASURED test).</text>')
    g.append(f'<text x="20" y="702" class="leg">Dashed: an assumption, or off the device. APPLE: Apple\'s own description. 0.7 GiB: the 300M models\' process.</text>')
    defs = f'<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker></defs>'
    style = f"""<style>
 .bt {{ font: 600 15px 'Plex Sans', sans-serif; fill: {INK}; }}
 .bl {{ font: 400 13px 'Plex Sans', sans-serif; fill: {MID}; }}
 .tag {{ font: 600 9.5px 'Plex Mono', monospace; letter-spacing: .8px; fill: {ACC}; }}
 .pt {{ font: 700 17px 'Plex Cond', 'Plex Sans', sans-serif; fill: {INK}; }}
 .pm {{ font: 600 14px 'Plex Mono', monospace; fill: {INK}; }}
 .cap {{ font: 400 11.5px 'Plex Mono', monospace; letter-spacing: 1px; fill: {MID}; }}
 .al {{ font: 400 12px 'Plex Mono', monospace; fill: {INK}; }}
 .leg {{ font: 400 12.5px 'Plex Sans', sans-serif; fill: {MID}; }}
</style>"""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Runtime of Apple Core Advanced on a Mac">{defs}{style}{"".join(g)}</svg>'


def page():
    css = table._fontfaces() + table.CSS % dict(P, width=W + 124)
    src = "Source: author's observation on a MacBook Pro, Apple M3 Max, 48 GB, macOS 27.0.1 (26A434): system log, fs_usage, powermetrics, footprint; no model file opened. The AI Realist, airealist.ai, October 24th and 25th, 2026"
    return f"""<!doctype html><meta charset="utf-8"><style>{css}</style>
<div class="sheet"><div class="wrap">
  <h1>One request, five models, two processes: how Core Advanced runs on a Mac</h1>
  <div class="sub">What a Mac shows from outside, October 2026</div>
  <div style="margin-top:26px">{svg()}</div>
  <div class="foot"><div class="src">{src}</div>{table._title_block(date(2026, 10, 26))}</div>
</div></div>"""


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else HERE.parents[1] / "plots" / "runtime-mac.png")
    html_path = out.with_suffix(".html")
    html_path.write_text(page(), encoding="utf-8")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(device_scale_factor=2, viewport={"width": W + 124, "height": 1000})
        pg.goto(f"file://{html_path.resolve()}")
        pg.wait_for_timeout(300)
        pg.locator(".sheet").screenshot(path=str(out))
        b.close()
    print("wrote", out)
