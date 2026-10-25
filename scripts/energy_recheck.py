#!/usr/bin/env python3
"""Independent recomputation of an energy run: different parser, different windowing, sensitivity to the window edges.
Usage: python3 energy_recheck.py [TAG]   (TAG empty for the 8-bit run, _4bit for the 4-bit run)"""
import datetime, json, re, statistics, sys
from pathlib import Path
D = Path(__file__).resolve().parents[1] / "data" / "compare"
TAG = sys.argv[1] if len(sys.argv) > 1 else ""
txt = (D / f"powermetrics_energy{TAG}.txt").read_text(errors="ignore")
ph = json.load(open(D / f"phases{TAG}.json"))
res = json.load(open(D / f"energy_results{TAG}.json"))
S = []
for blk in re.split(r"\*{3} Sampled system activity ", txt)[1:]:
    m = re.match(r"\(\w+ (\w+) +(\d+) (\d+):(\d+):(\d+) (\d+) ([+-]\d{4})\) \(([\d.]+)ms elapsed\)", blk)
    if not m: continue
    mon, d, H, M, Sx, Y, tz, el = m.groups()
    t = datetime.datetime.strptime(f"{Y} {mon} {d} {H}:{M}:{Sx} {tz}", "%Y %b %d %H:%M:%S %z").timestamp()
    f = lambda p: (float(re.search(p, blk).group(1)) if re.search(p, blk) else None)
    S.append(dict(t=t, dt=float(el) / 1000, cpu=f(r"CPU Power: ([\d.]+) mW"), gpu=f(r"GPU Power: ([\d.]+) mW"), ane=f(r"ANE Power: ([\d.]+) mW"), comb=f(r"Combined Power \(CPU \+ GPU \+ ANE\): ([\d.]+) mW")))
print("samples", len(S), "first", datetime.datetime.fromtimestamp(S[0]["t"]), "last", datetime.datetime.fromtimestamp(S[-1]["t"]))
print("missing fields", sum(1 for s in S if None in (s["cpu"], s["gpu"], s["ane"], s["comb"])))
bad = [s for s in S if abs((s["cpu"] + s["gpu"] + s["ane"]) - s["comb"]) > 2]
print("samples where cpu+gpu+ane differs from combined by >2 mW:", len(bad))
dts = [s["dt"] for s in S]
print("dt min/median/max", min(dts), statistics.median(dts), max(dts), " gaps between sample stamps >2 s:", sum(1 for a, b in zip(S, S[1:]) if b["t"] - a["t"] > 2))
def win(a, b): return [s for s in S if a <= s["t"] <= b]
base = next(p for p in ph["phases"] if p["name"] == "baseline_idle")
bw = win(base["start"], base["end"])
idle = sum(s["comb"] * s["dt"] for s in bw) / sum(s["dt"] for s in bw)
print(f"idle baseline {idle:.1f} mW over {len(bw)} samples; reported {res['idle_baseline_mw']}")
for p in ph["phases"]:
    if p["name"].startswith("idle_after"):
        w = win(p["start"], p["end"]); print(f"  {p['name']:32s} mean {sum(s['comb']*s['dt'] for s in w)/sum(s['dt'] for s in w):7.1f} mW over {len(w)} samples")
print()
for p in ph["phases"]:
    if "solved" not in p: continue
    r = res["models"][p["name"]]
    out = []
    for lo, hi in ((0, 0), (-1, 1), (1, -1), (-2, 2), (2, -2)):   # shrink or widen the window by whole seconds
        w = win(p["start"] + lo, p["end"] + hi); secs = sum(s["dt"] for s in w)
        e = sum((s["cpu"] + s["gpu"] + s["ane"]) * s["dt"] for s in w) / 1000 - idle * secs / 1000
        out.append(e)
    w = win(p["start"], p["end"]); secs = sum(s["dt"] for s in w)
    e = sum((s["cpu"] + s["gpu"] + s["ane"]) * s["dt"] for s in w) / 1000 - idle * secs / 1000
    mean = lambda k: sum(s[k] * s["dt"] for s in w) / secs
    peak = max(s["comb"] for s in w)
    print(f"{p['name']:16s} samples {len(w)} (expected ~{(p['end']-p['start'])/0.5:.0f}) secs {secs:6.1f} | energy above idle {e:7.1f} J (reported {r['energy_above_idle_j']}) | J/solved {e/p['solved']:.1f} (reported {r['j_per_solved_above_idle']}) | J/problem {e/p['problems']:.1f}")
    print(f"{'':16s} mean ANE {mean('ane'):.0f} GPU {mean('gpu'):.0f} CPU {mean('cpu'):.0f} mW; peak combined {peak:.0f} mW; window edges +-1s,+-2s energy: " + ", ".join(f"{x:.0f}" for x in out))
