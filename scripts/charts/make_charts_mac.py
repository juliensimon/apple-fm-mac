#!/usr/bin/env python3
"""Three more charts for the Mac-first piece, in the Datasheet brand: what it costs a Mac (storage and memory), the expert reads over time,
and speed against prompt length. Data: data/plots/*.csv (REPORT sections 14 and 21), data/compare/memory_footprint.json.
Run: uv run --quiet --with matplotlib --with numpy python scripts/charts/make_charts_mac.py [cost|trace|speed]   (default: all three)"""
import csv
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]                      # repository root
sys.path.insert(0, str(HERE))
from brand import ACCENT, GRID, INK, MONO, MUTED, PAPER, SANS, Sheet  # noqa: E402

PLOTS = ROOT / "data" / "plots"
IMG = ROOT / "plots"
DAY = date(2026, 10, 26)                    # the sheet number follows the publication date; update at publication
GREY = "#9AA3AE"
want = set(sys.argv[1:]) or {"cost", "trace", "speed", "energy", "memory"}


def rows(path):
    return list(csv.DictReader(open(path)))


if "speed" in want:
    r = rows(PLOTS / "ctx_profile.csv")
    by = defaultdict(list)
    for x in r:
        by[int(x["prompt_tokens"])].append(x)
    xs = sorted(by)
    ttft = [np.mean([float(x["ttft_s"]) for x in by[k]]) for k in xs]
    dec = [(k, np.mean([float(x["decode_tok_s"]) for x in by[k]])) for k in xs if by[k][0]["output_is_counting_task"] == "1"]
    # least-squares fits of time to first token on all 18 runs (two per length): a quadratic and, for contrast, a straight line
    rx = np.array([float(x["prompt_tokens"]) for x in r]); ry = np.array([float(x["ttft_s"]) for x in r])
    fits = {}
    for deg in (1, 2):
        c = np.polyfit(rx, ry, deg); res = ry - np.polyval(c, rx)
        fits[deg] = (c, 1 - (res ** 2).sum() / ((ry - ry.mean()) ** 2).sum())
    s = Sheet("substack", "Time to first token grows with the square of the prompt; writing speed halves by 5,000 tokens",
              "Apple's model on an M3 Max: time to first token and writing speed against prompt length",
              "Author's measurement through fm serve, macOS 27.0.1 (26A434), 2026-10-24, two runs per length; fits by least squares on all 18 runs. Writing speed is measured on a counting task of 172 tokens. Data: data/plots/ctx_profile.csv",
              day=DAY)
    x0, y0, w, h = s.body
    u = s.u
    for i, (head, data, unit, color) in enumerate((("Time to first token", list(zip(xs, ttft)), "s", GREY), ("Writing speed", dec, "tokens/s", ACCENT))):
        ax = s._axes([x0 + i * w / 2 + .035, y0 + .02, w / 2 - .075, h - .06])
        ax.spines["left"].set_visible(True); ax.spines["left"].set_color(INK); ax.tick_params(left=True, labelleft=True, labelsize=13 * u, colors=INK)
        px, py = zip(*data)
        if unit == "s":   # the measured runs as points, the quadratic fit in the accent, the straight line dashed for contrast
            gx = np.linspace(0, 7000, 200)
            (c2, r2q), (c1, r2l) = fits[2], fits[1]
            ax.plot(gx, np.polyval(c1, gx), color=MUTED, lw=1.6, ls=(0, (5, 4)), zorder=2)
            ax.plot(gx, np.polyval(c2, gx), color=ACCENT, lw=3, zorder=3)
            ax.plot(rx, ry, ls="none", marker="o", ms=8, mfc=PAPER, mec=INK, mew=1.6, zorder=4)
            ax.text(250, max(py) * 1.32, f"{c2[2]:.2f} s + {c2[1] * 1e3:.3f} ms × n + {c2[0] * 1e6:.3f} µs × n²   R² {r2q:.3f}",
                    font=MONO, fontsize=12.5 * u, color=ACCENT, va="top")
            ax.text(250, max(py) * 1.22, f"straight line, dashed   R² {r2l:.3f}", font=MONO, fontsize=12.5 * u, color=MUTED, va="top")
        else:
            ax.plot(px, py, color=color, lw=3, marker="o", ms=7, zorder=3)
        ax.yaxis.grid(True, color=GRID, lw=.8, zorder=0)
        ax.set_ylim(0, max(py) * (1.35 if unit == "s" else 1.2))
        ax.set_xlim(0, 7200)
        ax.set_xticks([0, 2000, 4000, 6000], ["0", "2,000", "4,000", "6,000"], font=MONO, fontsize=12 * u, color=MUTED)
        for k, v in (data[0], data[-1]):
            ax.text(k, v + max(py) * .05, f"{v:.1f}" if unit == "s" else f"{v:.0f}", font=MONO, fontsize=15 * u, fontweight="semibold", color=INK, ha="left" if k == px[0] else "center")
        ax.set_title(f"{head.upper()}  ·  {unit}  ·  PROMPT TOKENS ON THE X AXIS", loc="left", font=MONO, fontsize=11 * u, color=MUTED, pad=12)
    print(s.save(IMG / "speed-context.png"))

if "trace" in want:
    r = rows(PLOTS / "ifp_reads.csv")
    by = defaultdict(list)
    for x in r:
        by[x["phase"]].append(float(x["seconds_into_phase"]))
    panels = (("code", 519, 58, 9.6, "A code answer: 519 tokens at 58 a second"), ("essay", 3038, 33, 21.0, "A five-topic essay answer: 3,038 tokens at 33 a second (first 21 s)"))
    s = Sheet("substack", "The model reads its experts in bursts, about every 32 tokens",
              "Each bar counts the 294,912-byte reads in a 100 ms window; a reselection that loads nothing leaves no bar",
              "Author's measurement: fs_usage on the model's file, root run, macOS 27.0.1 (26A434), 2026-10-24; 1,384 reads, every one 294,912 bytes. The 32-token cadence is derived from burst spacing and decode speed. Data: data/plots/ifp_reads.csv",
              day=DAY)
    x0, y0, w, h = s.body
    u = s.u
    for i, (ph, ntok, tps, tmax, head) in enumerate(panels):
        ax = s._axes([x0 + .035, y0 + (1 - i) * h / 2 + .03, w - .07, h / 2 - .1])
        ax.spines["left"].set_visible(True); ax.spines["left"].set_color(INK); ax.tick_params(left=True, labelleft=True, labelsize=12 * u, colors=INK)
        t = np.array(by[ph]); t = t[t <= tmax]
        bins = np.arange(0, tmax + .1, .1)
        cnt, _ = np.histogram(t, bins=bins)
        ax.bar(bins[:-1], cnt, width=.085, align="edge", color=[ACCENT if b < .3 else GREY for b in bins[:-1]], zorder=3)
        ax.yaxis.grid(True, color=GRID, lw=.8, zorder=0)
        ax.set_xlim(0, tmax)
        ticks = list(np.arange(0, tmax + .1, 2 if tmax < 12 else 4))
        ax.set_xticks(ticks, [f"{t:g}" for t in ticks], font=MONO, fontsize=12 * u, color=MUTED)
        ax.text(.22, cnt.max() * .97, f"{int(cnt[:3].sum())} reads in the first burst", font=MONO, fontsize=13 * u, color=INK, va="top")
        ax.set_title(head.upper(), loc="left", font=MONO, fontsize=11 * u, color=MUTED, pad=10)
    print(s.save(IMG / "expert-reads.png"))

if "cost" in want:
    MEMDIR = HERE / "compare" if (HERE / "compare").exists() else ROOT / "data" / "compare"
    proto = json.load(open(MEMDIR / "memory_protocol.json"))
    fc = rows(PLOTS / "footprint_categories.csv")

    def to_mib(v):
        n, unit = v.split()
        return float(n) / {"B": 1048576, "KB": 1024, "MB": 1, "GB": 1 / 1024}[unit]

    def apple_after(pid):    # the process's whole footprint (dirty total) plus the Neural Engine memory that macOS leaves out of it
        out = ("Owned physical footprint (unmapped) (neural) (nofootprint)", "IOKit (neural) (nofootprint)")
        foot = sum(to_mib(r["dirty"]) for r in fc if r["snapshot"] == "after" and r["pid"] == pid and r["category"] == "TOTAL")
        return foot + sum(to_mib(r[c]) for r in fc if r["snapshot"] == "after" and r["pid"] == pid and r["category"] in out for c in ("dirty", "clean", "reclaimable"))

    main, second = apple_after("9704"), apple_after("9700")
    label = {"qwen3-4b": "Qwen3 4B", "gemma3-4b": "Gemma 3 4B", "gemma4-e4b": "Gemma 4 E4B", "gemma4-26b-a4b": "Gemma 4 26B A4B"}
    items = [("Apple's model alone", main / 1024), ("Apple's model and its safety models", (main + second) / 1024)]
    for r in proto:
        base, bits = r["label"].rsplit("-", 1)
        items.append((f"{label[base]}, {bits.replace('bit', '-bit')}", r["footprint_mib_after_2s"] / 1024))
    items.sort(key=lambda kv: kv[1])
    storage = [("Apple Intelligence (Apple, up to)", 14.0), ("Apple Intelligence (MacRumors)", 20.67),
               ("Qwen3 4B, 4-bit", 2.26), ("Qwen3 4B, 8-bit", 4.29), ("Gemma 3 4B, 4-bit", 3.4), ("Gemma 3 4B, 8-bit", 5.72), ("Gemma 4 E4B, 4-bit", 5.15), ("Gemma 4 E4B, 8-bit", 8.91)]
    storage.sort(key=lambda kv: kv[1])
    s = Sheet("substack", "Up to 14 GB of storage, then 1.3 to 2.0 GiB of memory two seconds after a long request",
              "Storage and memory: Apple's built-in model against the open builds I ran",
              "Memory: `footprint` two seconds after a 5,000-token request: Apple's two provider processes (data/plots/footprint_categories.csv) and each open build's mlx_lm.server (data/compare/memory_protocol.json). Storage: Apple page 121115, MacRumors (M4 Pro Mac mini), Hugging Face.",
              day=DAY)
    x0, y0, w, h = s.body
    u = s.u
    for i, (head, data, fmt) in enumerate((("Memory held two seconds after a long request, GiB", items, "{:.1f}"), ("Storage, GB", storage, "{:.1f}"))):
        gut = .17
        ax = s._axes([x0 + i * w / 2 + gut, y0 + .01, w / 2 - gut - .03, h - .05])
        ax.spines["bottom"].set_visible(False); ax.spines["left"].set_visible(True); ax.spines["left"].set_color(INK)
        labels, vals = zip(*data)
        ys = np.arange(len(labels))[::-1]
        colors = [ACCENT if l.startswith("Apple") else GREY for l in labels]
        ax.barh(ys, vals, color=colors, height=.62, zorder=3)
        ax.xaxis.grid(True, color=GRID, lw=.8, zorder=0)
        for y, v in zip(ys, vals):
            ax.text(v + max(vals) * .015, y, fmt.format(v), va="center", font=MONO, fontsize=14 * u, fontweight="semibold", color=INK)
        ax.set_yticks(ys, labels, font=SANS, fontsize=12.5 * u, color=INK); ax.tick_params(left=False, labelleft=True, bottom=False, labelbottom=False)
        ax.set_xlim(0, max(vals) * 1.2)
        ax.set_title(head.upper(), loc="left", font=MONO, fontsize=11 * u, color=MUTED, pad=12)
    print(s.save(IMG / "cost-mac.png"))

if "energy" in want:
    EDIR = HERE / "compare" if (HERE / "compare").exists() else ROOT / "data" / "compare"
    er = json.load(open(EDIR / "energy_results.json"))["models"]
    name = {"apple": "Apple's model (Neural Engine)", "gemma3-4b-8bit": "Gemma 3 4B, 8-bit (GPU)", "gemma4-e4b-8bit": "Gemma 4 E4B, 8-bit (GPU)", "qwen3-4b-8bit": "Qwen3 4B, 8-bit (GPU)"}
    order = sorted(er, key=lambda k: er[k]["j_per_solved_above_idle"])
    s = Sheet("substack", "Same 20 math problems: the Neural Engine model uses 35% to 56% of the open builds' energy per problem solved",
              "CPU + GPU + Neural Engine energy above idle, M3 Max, Apple's model against three open builds",
              "Author's measurement, powermetrics at 0.5 s (CPU, GPU and ANE power; memory, storage and display not counted), idle baseline 185 mW subtracted, first 20 of the 100 GSM8K problems, macOS 27.0.1 (26A434), 2026-10-25. Data: data/compare/energy_results.json",
              day=DAY)
    x0, y0, w, h = s.body
    u = s.u
    panels = (("Energy for the 20 problems, joules", lambda k: er[k]["energy_above_idle_j"], lambda k: f"{er[k]['energy_above_idle_j']:,.0f}   {er[k]['mean_combined_mw'] / 1000:.1f} W mean"),
              ("Joules per problem solved", lambda k: er[k]["j_per_solved_above_idle"], lambda k: f"{er[k]['j_per_solved_above_idle']:.0f}   ({er[k]['solved']} of 20 solved)"))
    for i, (head, val, lab) in enumerate(panels):
        gut = .17 if i == 0 else .02
        ax = s._axes([x0 + i * w / 2 + gut, y0 + .01, w / 2 - gut - .03, h - .05])
        ax.spines["bottom"].set_visible(False); ax.spines["left"].set_visible(True); ax.spines["left"].set_color(INK)
        ys = np.arange(len(order))[::-1]
        vals = [val(k) for k in order]
        ax.barh(ys, vals, color=[ACCENT if k == "apple" else GREY for k in order], height=.62, zorder=3)
        ax.xaxis.grid(True, color=GRID, lw=.8, zorder=0)
        for y, k, v in zip(ys, order, vals):
            ax.text(v + max(vals) * .015, y, lab(k), va="center", font=MONO, fontsize=14 * u, fontweight="semibold", color=INK)
        ax.set_yticks(ys, [name[k] for k in order] if i == 0 else [""] * len(order), font=SANS, fontsize=12.5 * u, color=INK)
        ax.tick_params(left=False, labelleft=(i == 0), bottom=False, labelbottom=False)
        ax.set_xlim(0, max(vals) * (2.0 if i == 0 else 1.55))
        ax.set_title(head.upper(), loc="left", font=MONO, fontsize=11 * u, color=MUTED, pad=12)
    print(s.save(IMG / "energy-mac.png"))

if "memory" in want:
    # one panel for the design section: Apple's per-prompt experts against dense open builds and a per-token mixture of experts
    MEMDIR = HERE / "compare" if (HERE / "compare").exists() else ROOT / "data" / "compare"
    proto = json.load(open(MEMDIR / "memory_protocol.json"))
    fc = rows(PLOTS / "footprint_categories.csv")

    def to_mib(v):
        n, unit = v.split()
        return float(n) / {"B": 1048576, "KB": 1024, "MB": 1, "GB": 1 / 1024}[unit]

    def apple_after(pid):
        out = ("Owned physical footprint (unmapped) (neural) (nofootprint)", "IOKit (neural) (nofootprint)")
        foot = sum(to_mib(r["dirty"]) for r in fc if r["snapshot"] == "after" and r["pid"] == pid and r["category"] == "TOTAL")
        return foot + sum(to_mib(r[c]) for r in fc if r["snapshot"] == "after" and r["pid"] == pid and r["category"] in out for c in ("dirty", "clean", "reclaimable"))

    label = {"qwen3-4b": "Qwen3 4B", "gemma3-4b": "Gemma 3 4B", "gemma4-e4b": "Gemma 4 E4B", "gemma4-26b-a4b": "Gemma 4 26B A4B, experts per token"}
    items = [("Apple Core Advanced, experts per prompt, with its safety models", (apple_after("9704") + apple_after("9700")) / 1024, ACCENT)]
    for r in proto:
        base, bits = r["label"].rsplit("-", 1)
        moe = base == "gemma4-26b-a4b"
        items.append((f"{label[base]}, {bits.replace('bit', '-bit')}" + ("" if moe else ", dense"), r["footprint_mib_after_2s"] / 1024, INK if moe else GREY))
    items.sort(key=lambda kv: kv[1])
    s = Sheet("substack", "Experts per prompt hold 2 GiB; experts per token hold 15",
              "Memory held two seconds after the same 5,000-token request, GiB, on a MacBook Pro M3 Max",
              "Author's measurement with footprint, macOS 27.0.1, 2026-10-24 and 25; Gemma 4 26B A4B to the nearest GB. Data: findings/04-memory",
              day=DAY)
    x0, y0, w, h = s.body
    u = s.u
    gut = .36
    ax = s._axes([x0 + gut, y0 + .01, w - gut - .06, h - .05])
    ax.spines["bottom"].set_visible(False); ax.spines["left"].set_visible(True); ax.spines["left"].set_color(INK)
    labels, vals, colors = zip(*items)
    ys = np.arange(len(labels))[::-1]
    ax.barh(ys, vals, color=colors, height=.62, zorder=3)
    ax.xaxis.grid(True, color=GRID, lw=.8, zorder=0)
    for y, v in zip(ys, vals):
        ax.text(v + max(vals) * .012, y, f"{v:.0f}" if v > 10 else f"{v:.1f}", va="center", font=MONO, fontsize=15 * u, fontweight="semibold", color=INK)
    ax.set_yticks(ys, labels, font=SANS, fontsize=13 * u, color=INK); ax.tick_params(left=False, labelleft=True, bottom=False, labelbottom=False)
    ax.set_xlim(0, max(vals) * 1.12)
    print(s.save(IMG / "memory-mac.png"))
