#!/usr/bin/env python3
"""Energy per solved problem from powermetrics_energy.txt and phases.json (see energy_workload.py and run_energy.sh).
"Combined Power (CPU + GPU + ANE)" per sample (memory, storage and display are not in it), integrated over each model's timed window (sample power x sample length),
minus the idle baseline power times the window length. Joules per solved problem = that energy / problems solved.
Usage: python3 energy_analyze.py [powermetrics_energy.txt] [phases.json]"""
import csv
import datetime
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TAG = sys.argv[3] if len(sys.argv) > 3 else ""
pm = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / f"powermetrics_energy{TAG}.txt"
ph = json.load(open(sys.argv[2] if len(sys.argv) > 2 else HERE / f"phases{TAG}.json"))
txt = pm.read_text(errors="ignore")
samples = []
for blk in txt.split("*** Sampled system activity")[1:]:
    m = re.search(r"\(\w+ (\w+) +(\d+) (\d+):(\d+):(\d+) (\d+) ([+-]\d{4})\)", blk)
    if not m:
        continue
    mon, d, H, M, S, Y, tz = m.groups()
    ts = datetime.datetime.strptime(f"{Y} {mon} {d} {H}:{M}:{S} {tz}", "%Y %b %d %H:%M:%S %z").timestamp()
    el = re.search(r"\(([\d.]+)ms elapsed\)", blk)
    def g(p):
        mm = re.search(p, blk); return float(mm.group(1)) if mm else None
    samples.append({"t": ts, "dt": float(el.group(1)) / 1000 if el else 0.5, "combined": g(r"Combined Power \(CPU \+ GPU \+ ANE\):\s*([\d.]+)"),
                    "ane": g(r"ANE Power:\s*([\d.]+)"), "gpu": g(r"GPU Power:\s*([\d.]+)"), "cpu": g(r"CPU Power:\s*([\d.]+)")})
base = next(p for p in ph["phases"] if p["name"] == "baseline_idle")
bs = [s for s in samples if base["start"] <= s["t"] <= base["end"] and s["combined"] is not None]
idle_mw = sum(s["combined"] for s in bs) / len(bs)
out = {"idle_baseline_mw": round(idle_mw, 1), "baseline_samples": len(bs), "models": {}}
rows = []
for p in ph["phases"]:
    if "solved" not in p:
        continue
    w = [s for s in samples if p["start"] <= s["t"] <= p["end"] and s["combined"] is not None]
    secs = sum(s["dt"] for s in w)
    mean = lambda k: sum(s[k] * s["dt"] for s in w if s[k] is not None) / secs
    energy_j = sum(s["combined"] * s["dt"] for s in w) / 1000
    net_j = energy_j - idle_mw * secs / 1000
    r = {"model": p["name"], "problems": p["problems"], "solved": p["solved"], "window_s": round(p["end"] - p["start"], 1), "samples": len(w),
         "mean_combined_mw": round(mean("combined")), "mean_ane_mw": round(mean("ane")), "mean_gpu_mw": round(mean("gpu")), "mean_cpu_mw": round(mean("cpu")),
         "request_errors": len(p.get("errors", [])), "energy_j": round(energy_j, 1), "energy_above_idle_j": round(net_j, 1),
         "j_per_solved_above_idle": round(net_j / p["solved"], 1) if p["solved"] else None, "j_per_problem_above_idle": round(net_j / p["problems"], 1)}
    out["models"][p["name"]] = r; rows.append(r)
json.dump(out, open(HERE / f"energy_results{TAG}.json", "w"), indent=1)
with open(HERE / f"energy_results{TAG}.csv", "w", newline="") as f:
    wtr = csv.DictWriter(f, fieldnames=list(rows[0])); wtr.writeheader(); wtr.writerows(rows)
print(f"idle baseline {idle_mw:.0f} mW over {len(bs)} samples")
for r in rows:
    print(f"{r['model']:18s} solved {r['solved']:2d}/{r['problems']}  window {r['window_s']:6.1f} s  mean {r['mean_combined_mw']:6d} mW (ANE {r['mean_ane_mw']}, GPU {r['mean_gpu_mw']}, CPU {r['mean_cpu_mw']})  "
          f"above idle {r['energy_above_idle_j']:7.1f} J  = {r['j_per_solved_above_idle']} J per solved problem  ({r['request_errors']} request errors)")
