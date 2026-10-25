#!/usr/bin/env python3
"""Black-box timing of `fm respond`: prefill vs prompt length, decode speed, determinism."""
import json, os, subprocess, sys, time

ENV = dict(os.environ, NO_COLOR="1", TERM="dumb")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bench.json")


def ct(text):
    r = subprocess.run(["fm", "count-tokens", "-q", "--", text], capture_output=True, text=True, env=ENV, stdin=subprocess.DEVNULL, timeout=120)
    return int(r.stdout.strip())


def respond(prompt, greedy=True, instructions=None):
    cmd = ["fm", "respond", "--stream"] + (["-g"] if greedy else [])
    if instructions:
        cmd += ["-i", instructions]
    cmd += ["--", prompt]
    t0 = time.perf_counter()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV, stdin=subprocess.DEVNULL)
    first = None
    chunks = []
    while True:
        b = p.stdout.read1(65536)
        if not b:
            break
        now = time.perf_counter()
        if first is None:
            first = now - t0
        chunks.append((now - t0, len(b)))
    p.wait()
    total = time.perf_counter() - t0
    text = b"".join([]).decode()  # placeholder, text re-read below
    return first, total, chunks, p.stderr.read().decode()[:300]


def respond_text(prompt, greedy=True):
    cmd = ["fm", "respond", "--no-stream"] + (["-g"] if greedy else []) + ["--", prompt]
    t0 = time.perf_counter()
    r = subprocess.run(cmd, capture_output=True, text=True, env=ENV, stdin=subprocess.DEVNULL, timeout=300)
    return time.perf_counter() - t0, r.stdout, r.stderr[:300]


res = {}
# 0. baseline process start + tiny answer
res["tiny"] = [respond_text("Reply with the single word OK.")[0] for _ in range(3)]

# 1. prefill scaling: long filler prompt, ask for one word
filler = "The quick brown fox jumps over the lazy dog near the quiet river. "
for n in (50, 200, 500, 1000, 2000, 3000):
    prompt = filler * (n // 14 + 1)
    toks = ct(prompt)
    dt, out, err = respond_text(prompt + "\n\nReply with the single word DONE.")
    res.setdefault("prefill", []).append({"prompt_tokens": toks, "seconds": dt, "out": out.strip()[:80], "err": err})
    print("prefill", toks, round(dt, 2), out.strip()[:60].replace("\n", " "), err[:120], flush=True)

# 2. decode speed: stream a long answer
first, total, chunks, err = respond("Write a 250 word description of a lighthouse keeper's morning routine.")
res["decode_stream"] = {"first_chunk_s": first, "total_s": total, "chunks": chunks, "err": err}
print("stream first", round(first or -1, 3), "total", round(total, 3), "chunks", len(chunks), flush=True)

# 3. output token count for the same prompt (non-streamed greedy) to get tokens/s
dt, text, err = respond_text("Write a 250 word description of a lighthouse keeper's morning routine.")
n_out = ct(text)
res["decode_nostream"] = {"seconds": dt, "out_tokens": n_out, "chars": len(text)}
print("nostream", round(dt, 2), "out tokens", n_out, flush=True)

# 4. determinism: greedy x3, sampled x3
g = [respond_text("Give me a one-sentence fact about octopuses.")[1] for _ in range(3)]
s = [respond_text("Give me a one-sentence fact about octopuses.", greedy=False)[1] for _ in range(3)]
res["greedy_identical"] = len(set(g)) == 1
res["sampled_distinct"] = len(set(s))
res["greedy_samples"] = g
res["sampled_samples"] = s
print("greedy identical:", res["greedy_identical"], "sampled distinct:", res["sampled_distinct"], flush=True)

json.dump(res, open(OUT, "w"), indent=1)
