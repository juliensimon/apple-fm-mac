#!/usr/bin/env python3
"""Does DRAM contention slow the on-device model? Run fm under CPU bandwidth hogs of different strength.
Run: cc -O2 -o data/membw data/membw.c && python3 data/contention.py   (seven loads of 75 seconds each; writes data/contention.json)"""
import json, os, subprocess, time

ENV = dict(os.environ, NO_COLOR="1", TERM="dumb")
HERE = os.path.dirname(os.path.abspath(__file__))
FILLER = "The quick brown fox jumps over the lazy dog near the quiet river. "
TAIL = "\nCount from 1 to 60, separated by commas, and write nothing else."
_ct_cache = {}


def ct(text):
    if text not in _ct_cache:
        r = subprocess.run(["fm", "count-tokens", "-q", "--", text], capture_output=True, text=True, env=ENV, stdin=subprocess.DEVNULL, timeout=120)
        _ct_cache[text] = int(r.stdout.strip())
    return _ct_cache[text]


def stream(prompt):
    t0 = time.perf_counter()
    p = subprocess.Popen(["fm", "respond", "--stream", "-g", "--", prompt], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV, stdin=subprocess.DEVNULL)
    first = last = None; buf = b""
    while True:
        b = p.stdout.read1(65536)
        if not b: break
        now = time.perf_counter() - t0
        if first is None: first = now
        last = now; buf += b
    p.wait()
    return first, last, buf.decode(errors="replace")


def decode_run(prompt):
    first, last, out = stream(prompt)
    if first is None: return {"error": out[:80]}
    n_out = ct(out)
    return {"ttft_s": round(first, 3), "decode_s": round(last - first, 3), "out_tokens": n_out, "tok_s": round((n_out - 1) / (last - first), 2) if last > first else None}


def prefill_run(prompt):
    first, last, out = stream(prompt)
    return {"ttft_s": round(first, 3) if first else None, "out": out.strip()[:20]}


SHORT = TAIL.strip()
LONG = (FILLER * 326) + TAIL
MID = (FILLER * 140) + "\nReply with the single word DONE."
CONDITIONS = [("none", None), ("read x1", ("1", "read")), ("read x4", ("4", "read")), ("copy x4", ("4", "copy")),
              ("copy x12", ("12", "copy")), ("spin x12 (control)", ("12", "spin")), ("none (again)", None)]
results = []
for name, hog in CONDITIONS:
    proc = None; hogfile = os.path.join(HERE, "hog_%d.txt" % len(results))
    if hog:
        proc = subprocess.Popen([os.path.join(HERE, "membw"), hog[0], "75", "256" if hog[1] != "spin" else "1", hog[1]], stdout=open(hogfile, "w"), stderr=subprocess.DEVNULL)
        time.sleep(4)
    t_start = time.time()
    rec = {"condition": name, "short_decode": [decode_run(SHORT) for _ in range(2)], "long_decode": [decode_run(LONG)], "prefill_2k": [prefill_run(MID) for _ in range(2)]}
    t_end = time.time()
    if proc: proc.wait()
    bw = None
    if hog:
        lines = [l.split() for l in open(hogfile) if l[0].isdigit()]
        # lines are "<elapsed> <GBps>"; average the seconds that overlap the measurement window
        vals = [float(b) for a, b in lines if 3 <= float(a) <= 4 + (t_end - t_start)]
        bw = round(sum(vals) / len(vals), 1) if vals else None
    rec["hog_gbps_during"] = bw
    results.append(rec)
    json.dump(results, open(os.path.join(HERE, "contention.json"), "w"), indent=1)
    s = rec["short_decode"]; l = rec["long_decode"][0]; p = rec["prefill_2k"]
    print(f"{name:20s} hog={bw!s:>6} GB/s | short decode {s[0].get('tok_s')}, {s[1].get('tok_s')} tok/s | long (4.7k ctx) decode {l.get('tok_s')} tok/s ttft {l.get('ttft_s')} | prefill 2k {p[0]['ttft_s']}, {p[1]['ttft_s']} s", flush=True)
    time.sleep(3)
print("done")
