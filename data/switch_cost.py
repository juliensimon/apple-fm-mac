"""Adapter switching cost (REPORT 23.4): alternate the general and content-tagging use cases on one prompt, 19 runs.
Run: python3 data/switch_cost.py   (writes data/switch_cost.json)"""
import json, os, subprocess, time, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
ENV = dict(os.environ, NO_COLOR="1", TERM="dumb")
PROMPT = "Tag the topics: GPUs double inference throughput for small language models on laptops."
def run(use_case):
    cmd = ["fm", "respond", "--stream", "-g"] + (["--use-case", use_case] if use_case != "general" else []) + ["--", PROMPT]
    t0 = time.perf_counter(); p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV, stdin=subprocess.DEVNULL)
    first = None; buf = b""
    while True:
        b = p.stdout.read1(65536)
        if not b: break
        if first is None: first = time.perf_counter() - t0
        buf += b
    p.wait(); return first, time.perf_counter() - t0, len(buf)
seq = ["general"] * 4 + ["content-tagging"] * 4 + ["general", "content-tagging"] * 4 + ["general"] * 3
rows = []; prev = None
for uc in seq:
    first, total, n = run(uc); rows.append({"use_case": uc, "after": prev, "ttft_s": round(first, 3), "total_s": round(total, 3), "out_bytes": n}); prev = uc
    time.sleep(1.2)
json.dump(rows, open(os.path.join(HERE, "switch_cost.json"), "w"), indent=1)
def mean(f): 
    v = [r["total_s"] for r in rows if f(r)]; return round(st.mean(v), 3), len(v)
print("use case         after              total seconds (mean, n)")
for uc in ("general", "content-tagging"):
    for after in ("general", "content-tagging"):
        print(f"{uc:16s} {after:16s}  {mean(lambda r: r['use_case']==uc and r['after']==after)}")
print("\nrun-by-run:", [(r["use_case"][:3], r["after"][:3] if r["after"] else "-", r["total_s"]) for r in rows])
