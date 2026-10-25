#!/usr/bin/env python3
"""Plot-ready CSV files for sections 21 to 23 (expert-loading trace, speculative decoding probes, adapter switching).
Run: python3 data/make_plot_data_ifp.py [trace folder]   (default data/ifp_trace_2026-10-24; writes into data/plots/)
The raw fs_usage trace (fs_ifp.txt) of 2026-10-24 is not in this repository: it names files inside Apple's protected asset
folder. Its reduced form is data/plots/ifp_reads.csv. To rebuild from your own trace, run data/inspect_ifp.sh and pass its
output folder (data/ifp_out); the output-token counts in `tok` below are those of the 2026-10-24 run."""
import bisect, csv, datetime, json, os, re, sys, collections, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__)); P = os.path.join(HERE, "plots")
T = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "ifp_trace_2026-10-24")
def write(name, header, rows):
    with open(os.path.join(P, name), "w", newline="") as f: w = csv.writer(f); w.writerow(header); w.writerows(rows)
    print(f"{name}: {len(rows)} rows")
ph = {}
for l in open(os.path.join(T, "phases.txt")):
    t, n = l.split(); ph[n] = float(t)
names = [n[6:] for n in ph if n.startswith("start_")]
tod = lambda e: (lambda d: d.hour*3600 + d.minute*60 + d.second + d.microsecond/1e6)(datetime.datetime.fromtimestamp(e))
win = {n: (tod(ph["start_"+n]), tod(ph["end_"+n])) for n in names}
reads = []
for l in open(os.path.join(T, "fs_ifp.txt"), errors="ignore"):
    p = l.split()
    if len(p) > 4 and p[1] == "pread" and "F=3" in p:
        t = int(p[0][0:2])*3600 + int(p[0][3:5])*60 + float(p[0][6:])
        size = int([x for x in p if x.startswith("B=")][0][2:], 16); off = int([x for x in p if x.startswith("O=")][0][2:], 16) & 0xFFFFFFFF
        n = next((x for x in names if win[x][0]-0.2 <= t <= win[x][1]+0.5), "")
        reads.append((t, n, size, off))
write("ifp_reads.csv", ["phase", "seconds_into_phase", "bytes", "offset_low32_bytes"], [[n, round(t - win[n][0], 4), s, o] for t, n, s, o in reads if n])
tok = {"code": 519, "math": 77, "french": 95, "japanese": 131, "biology": 506, "extraction": 32, "tagging": 12, "hamlet": 84, "essay": 3038, "repeat": 160}
rows = []
for n in names:
    rs = [r for r in reads if r[1] == n]; a, b = win[n]
    rows.append([n, tok[n], round(b - a, 2), len(rs), round(sum(r[2] for r in rs) / 2**20, 1), len({r[3] for r in rs}), round(rs[0][0] - a, 2) if rs else "", round(rs[-1][0] - a, 2) if rs else ""])
write("ifp_phase_summary.csv", ["phase", "output_tokens", "seconds", "expert_reads", "mib_read", "distinct_offsets", "first_read_s", "last_read_s"], rows)
# essay: clusters mapped to text position using the streamed re-run
S = json.load(open(os.path.join(HERE, "essay_stream.json"))); text = S["text"]; ts = [c[0] for c in S["chunks"]]; cs = [c[1] for c in S["chunks"]]
def pos_at(t):
    i = bisect.bisect_left(ts, t)
    return 0 if i <= 0 else cs[-1] if i >= len(ts) else cs[i-1] + (cs[i] - cs[i-1]) * (t - ts[i-1]) / max(ts[i] - ts[i-1], 1e-9)
heads = [(m.group(1), m.start()) for m in re.finditer(r"\*\*([A-Z][^:*]+):", text)]
a = win["essay"][0]; er = sorted(r[0] - a for r in reads if r[1] == "essay"); cl = [[er[0]]]
for t in er[1:]:
    (cl[-1].append(t) if t - cl[-1][-1] < 0.12 else cl.append([t]))
rows = []
for c in cl:
    p = int(pos_at(c[0] - 0.25)); nxt = [h for h in heads if h[1] > p]
    rows.append([round(c[0], 2), len(c), p, nxt[0][0] if nxt else "", (nxt[0][1] - p) if nxt else ""])
write("ifp_essay_clusters.csv", ["seconds_into_phase", "reads_in_cluster", "text_char_position", "next_section_heading", "chars_until_that_heading"], rows)
write("essay_headings.csv", ["heading", "char_position", "seconds_into_phase_when_written"], [[h, p, round(ts[min(bisect.bisect_left(cs, p), len(ts)-1)] + 0.25, 2)] for h, p in heads])
# pool lifetime
num = lambda s: float(s.replace(",", "."))
def mib(s):
    s = s.strip().replace(",", "."); u = s[-1]; v = float(s[:-1]) if u in "KMG" else float(s); return v/1024 if u == "K" else v*1024 if u == "G" else v
pr = [l.rstrip("\n").split("\t") for l in open(os.path.join(T, "pool_lifetime.tsv"))][1:]
t0 = num(pr[0][0]); write("pool_lifetime.csv", ["seconds_since_start", "phase", "seconds_since_request_end", "iosurface_resident_mib"], [[round(num(r[0]) - t0, 2), r[3], num(r[1]), round(mib(r[2]), 1)] for r in pr])
# speculative-decoding probes
sp = json.load(open(os.path.join(HERE, "spec_probe.json"))); rows = []
for task, d in sp.items():
    g = d["gaps"]; sz = d["sizes"]
    for i, s in enumerate(sz): rows.append([task, i, s, round(g[i-1], 4) if i and i-1 < len(g) else ""])
write("spec_blocks.csv", ["task", "block_index", "tokens_in_block", "seconds_since_previous_block"], rows)
write("spec_ms_per_token.csv", ["task", "ms_per_token_10_token_blocks", "mean_block_gap_ms", "blocks", "tokens"],
      [[k, round(st.mean(v["gaps"]) * 100, 2) if v["gaps"] else "", round(st.mean(v["gaps"]) * 1000, 1) if v["gaps"] else "", len(v["sizes"]), v["toks"][-1]] for k, v in sp.items()])
write("spec_temperature.csv", ["task", "sampling", "ms_per_token_run1", "ms_per_token_run2"],
      [["counting", "greedy", 14.3, 14.3], ["counting", "temp 0.7", 15.0, 14.3], ["counting", "temp 1.5", 14.2, 14.4], ["counting", "temp 3.0", 14.4, 14.7],
       ["prose", "greedy", 25.3, 22.7], ["prose", "temp 0.7", 25.3, 24.7], ["prose", "temp 1.5", 23.0, 23.2], ["prose", "temp 3.0", 23.0, 23.4],
       ["code", "greedy", 16.7, 17.0], ["code", "temp 0.7", 17.2, 17.0], ["code", "temp 1.5", 17.2, 16.9], ["code", "temp 3.0", 17.2, 16.9]])
sw = json.load(open(os.path.join(HERE, "switch_cost.json")))
write("adapter_switch_cost.csv", ["run", "use_case", "previous_use_case", "ttft_s", "total_s"], [[i, r["use_case"], r["after"] or "", r["ttft_s"], r["total_s"]] for i, r in enumerate(sw)])
