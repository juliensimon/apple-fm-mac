"""Speculative-decoding probes (REPORT 22): stream ten tasks of different predictability through the public Swift API and record
when each token arrives. Needs the compiled helper:
  mkdir -p data/swiftq && swiftc -O -parse-as-library data/stream_snapshots.swift -o data/swiftq/stream
Run: python3 data/spec_probe.py   (writes data/spec_probe.json)"""
import collections, json, os, statistics as st, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(HERE, "swiftq", "stream")
COPY = ("The committee reviewed the annual budget on Tuesday afternoon and approved three amendments: a small increase for library hours, "
        "a freeze on travel spending, and a one-time grant for the community garden. The treasurer noted that revenues had come in slightly above forecast.")
TASKS = [
    ("letter A x150", "Output the letter A 150 times separated by single spaces and nothing else."),
    ("word echo x100", "Write the word echo 100 times separated by single spaces and nothing else."),
    ("counting 1..60", "Count from 1 to 60, separated by commas, and write nothing else."),
    ("repeat sentence", 'Write the sentence "The cat sat on the mat." exactly 20 times, one per line, and nothing else.'),
    ("copy a paragraph", "Repeat the following text exactly, word for word, and nothing else:\n" + COPY),
    ("code", "Write a Python function that merges two sorted lists, with three unit tests."),
    ("prose", "Write a 250 word description of a lighthouse keeper's morning routine."),
    ("pi digits", "Write the first 100 decimal digits of pi, separated by spaces, and nothing else."),
    ("random words", "Write 100 random, unrelated English words separated by spaces. Do not repeat any word."),
    ("primes", "List the first 60 prime numbers separated by commas and nothing else."),
]
def run(label, prompt):
    out = subprocess.run([BIN, label, "200", prompt], capture_output=True, text=True, timeout=300).stdout.splitlines()
    rows = [l.split("\t") for l in out if l and not l.startswith("#") and not l.startswith("t_s")]
    ts = [float(r[0]) for r in rows]; toks = [int(r[2]) for r in rows]
    meta = [l for l in out if l.startswith("#meta") or l.startswith("#final")]
    return ts, toks, meta
res = {}
for label, prompt in TASKS:
    ts, toks, meta = run(label, prompt)
    if not ts: print(label, "no rows"); continue
    groups = [[0]]
    for i in range(1, len(ts)):
        if ts[i] - ts[i-1] < 0.002: groups[-1].append(i)
        else: groups.append([i])
    sizes = [len(g) for g in groups]
    gaps = [ts[g[0]] - ts[prev[0]] for prev, g in zip(groups, groups[1:])]
    dur = ts[-1] - ts[0]
    h = collections.Counter(min(s, 20) for s in sizes)
    print(f"{label:22s} tokens {toks[-1]:4d}  decode {dur:5.2f}s  {toks[-1]/max(ts[-1],1e-9):5.1f} tok/s (incl. TTFT {ts[0]:.2f}s)  groups {len(groups):3d}  mean size {st.mean(sizes):5.2f}  max {max(sizes):3d}  mean gap {st.mean(gaps)*1000 if gaps else 0:6.1f} ms")
    print("      size histogram:", sorted(h.items()))
    res[label] = {"ts": ts, "toks": toks, "sizes": sizes, "gaps": gaps}
json.dump(res, open(os.path.join(HERE, "spec_probe.json"), "w"))
