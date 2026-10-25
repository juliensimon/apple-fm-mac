"""Does temperature change decode speed? Counting, prose and code under greedy and sampled decoding (REPORT 22.2).
Needs the helper built for spec_probe.py (data/swiftq/stream). Run: python3 data/spec_temp.py   (prints a table)"""
import collections, json, os, statistics as st, subprocess
BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "swiftq", "stream")
COUNT ="Count from 1 to 60, separated by commas, and write nothing else."
PROSE = "Write a 250 word description of a lighthouse keeper's morning routine."
CODE = "Write a Python function that merges two sorted lists, with three unit tests."
rows = []
def run(label, mode, prompt, runs=2):
    res = []
    for _ in range(runs):
        out = subprocess.run([BIN, label, "160", mode, prompt], capture_output=True, text=True, timeout=300).stdout.splitlines()
        r = [l.split("\t") for l in out if l and not l.startswith("#") and not l.startswith("t_s")]
        if not r or not r[0][0].replace(".", "").isdigit(): continue
        ts = [float(x[0]) for x in r]; toks = [int(x[2]) for x in r]
        # skip the first three delivery blocks (ramp), use the steady part
        groups = [[0]]
        for i in range(1, len(ts)):
            (groups[-1].append(i) if ts[i] - ts[i-1] < 0.002 else groups.append([i]))
        steady = groups[3:]
        if len(steady) < 3: continue
        n_tok = sum(len(g) for g in steady[:-1]); span = ts[steady[-1][0]] - ts[steady[0][0]]
        res.append((span / n_tok * 1000, toks[-1]))
    return res
print("task    sampling        ms per token (runs)        output tokens")
for task, p in (("counting", COUNT), ("prose", PROSE), ("code", CODE)):
    for mode in ("greedy", "temp:0.7", "temp:1.5", "temp:3.0"):
        r = run(task, mode, p)
        print(f"{task:9s} {mode:10s}   " + "  ".join(f"{m:6.1f}" for m, _ in r) + "          " + str([t for _, t in r]), flush=True)
