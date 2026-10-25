#!/usr/bin/env python3
"""Black-box profile of fm: time to first token and decode speed against context length."""
import json, os, subprocess, sys, time

ENV = dict(os.environ, NO_COLOR="1", TERM="dumb")
HERE = os.path.dirname(os.path.abspath(__file__))
FILLER = "The quick brown fox jumps over the lazy dog near the quiet river. "
TAIL = "\nCount from 1 to 60, separated by commas, and write nothing else."


def ct(text):
    r = subprocess.run(["fm", "count-tokens", "-q", "--", text], capture_output=True, text=True, env=ENV, stdin=subprocess.DEVNULL, timeout=120)
    return int(r.stdout.strip())


def run(prompt):
    t0 = time.perf_counter()
    p = subprocess.Popen(["fm", "respond", "--stream", "-g", "--", prompt], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV, stdin=subprocess.DEVNULL)
    first = last = None
    buf = b""
    while True:
        b = p.stdout.read1(65536)
        if not b:
            break
        now = time.perf_counter() - t0
        if first is None:
            first = now
        last = now
        buf += b
    p.wait()
    return first, last, buf.decode(errors="replace"), time.perf_counter() - t0


rows = []
base_tail = ct(TAIL)
for reps in (0, 35, 70, 140, 210, 280, 350, 420, 490):
    prompt = (FILLER * reps) + TAIL
    n_prompt = ct(prompt)
    for rep in range(2):
        first, last, out, total = run(prompt)
        n_out = ct(out)
        decode_s = (last - first) if first is not None else None
        rate = (n_out - 1) / decode_s if decode_s and decode_s > 0 else None
        rows.append({"reps": reps, "prompt_tokens": n_prompt, "rep": rep, "ttft_s": first, "decode_s": decode_s, "out_tokens": n_out, "decode_tok_s": rate, "total_s": total})
        print(f"prompt={n_prompt:5d} rep={rep} ttft={first:6.2f}s out={n_out:4d} decode={decode_s:6.2f}s -> {rate:6.1f} tok/s  err={out[:30]!r}" if first else f"prompt={n_prompt} failed {out[:80]!r}", flush=True)
json.dump(rows, open(os.path.join(HERE, "profile_ctx.json"), "w"), indent=1)
