#!/usr/bin/env python3
"""Count the tokens of every reserved-slot string `<unusedN>`, N = 0 to 6241, through `fm count-tokens`.
The CLI returns one token more than the text alone; that offset is subtracted. A count of 1 means the slot is still a
single vocabulary entry for Apple's tokenizer. Gemma 3 has 6,242 such entries (0 to 6241). Writes unused_scan_full.json.
Run: python3 data/card_inputs/scan_unused.py   (6,242 calls to fm count-tokens)"""
import json, os, subprocess, time

os.chdir(os.path.dirname(os.path.abspath(__file__)))   # the output is written beside this script
ENV = dict(os.environ, NO_COLOR="1", TERM="dumb")
out = {}
t0 = time.time()
for n, i in enumerate(range(0, 6242)):
    try:
        r = subprocess.run(["fm", "count-tokens", "-q", "--", f"<unused{i}>"], capture_output=True, text=True, env=ENV,
                           stdin=subprocess.DEVNULL, timeout=30)
        out[i] = int(r.stdout.strip()) - 1
    except Exception:
        out[i] = None
    if n % 500 == 499:
        print(f"{n + 1}/6242 done, {time.time() - t0:.0f}s", flush=True)
        json.dump(out, open("unused_scan_full.json", "w"))
json.dump(out, open("unused_scan_full.json", "w"))

multi = [i for i, v in out.items() if v and v > 1]
single = [i for i, v in out.items() if v == 1]
failed = [i for i, v in out.items() if v is None]
print(f"slots scanned: {len(out)}; single token: {len(single)}; more than one token: {len(multi)}; failed: {len(failed)}")
print("more than one token, ranges:", [(a, b) for a, b in zip([multi[0]] + [m for p, m in zip(multi, multi[1:]) if m != p + 1],
                                                                   [p for p, m in zip(multi, multi[1:]) if m != p + 1] + [multi[-1]])])
print("token counts of those slots:", {k: sum(1 for i in multi if out[i] == k) for k in sorted({out[i] for i in multi})})
print("done")
