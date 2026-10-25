#!/usr/bin/env python3
"""Does Google's own token counter return Apple's counts? Sends the 257 public test strings to the Gemini API's countTokens
endpoint (it counts, it generates nothing) and compares each count with the count from `fm count-tokens` on the Mac.

The run of 2026-10-24 selected these 257 strings from the 429-string corpus: the multilingual sentences, the numbers/URLs/emoji,
the rare-word sentences and the code lines, minus any string with a user name, a path or a project name. The English prose and
the sentences from the author's report were not sent. This copy reads the same 257 strings, in the same order, from
data/tokenizer_test/strings_public.csv, so it writes the same file structure.

The API key is read from the environment at run time and never printed.
Run: GEMINI_API_KEY=<your key> python3 data/gemini_counttokens.py            (writes gemini_counttokens.json beside this file)
"""
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
STRINGS = HERE / "tokenizer_test" / "strings_public.csv"
MODELS = ["gemini-3-flash-preview", "gemini-3.1-pro-preview", "gemini-3.8-flash", "gemma-4-31b-it"]

key = os.environ.get("GEMINI_API_KEY", "").strip()
if not key:
    sys.exit("set GEMINI_API_KEY first")


def count(model, text):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:countTokens"
    body = json.dumps({"contents": [{"parts": [{"text": text}]}]}).encode()
    for attempt in range(6):
        req = urllib.request.Request(url, data=body, headers={"x-goog-api-key": key, "Content-Type": "application/json"})
        try:
            return json.load(urllib.request.urlopen(req, timeout=60))["totalTokens"]
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503):
                time.sleep(2 ** attempt)
                continue
            return f"HTTP {e.code}"
        except Exception:  # network hiccup
            time.sleep(1 + attempt)
    return "failed"


# per string: its category, its text and Apple's count of the text alone (fm count-tokens -q, minus the one extra token)
rows = [{"category": r["category"], "string": r["text"], "apple": int(r["apple_fm"])} for r in csv.DictReader(open(STRINGS, newline=""))]
print(len(rows), "strings to send;", len(MODELS), "models", flush=True)

out = {"strings": rows, "models": {}}
for m in MODELS:
    with ThreadPoolExecutor(6) as ex:
        counts = list(ex.map(lambda r: count(m, r["string"]), rows))
    ok = [c for c in counts if isinstance(c, int)]
    exact = sum(1 for r, c in zip(rows, counts) if c == r["apple"])
    off = {}
    for r, c in zip(rows, counts):
        if isinstance(c, int):
            off[c - r["apple"]] = off.get(c - r["apple"], 0) + 1
    out["models"][m] = {"counts": counts, "answered": len(ok), "exact_match_with_apple": exact, "difference_histogram": dict(sorted(off.items()))}
    print(f"{m:26s} answered {len(ok)}/{len(rows)}  equal to Apple's count: {exact}  differences (model minus Apple): {dict(sorted(off.items()))}", flush=True)

json.dump(out, open(HERE / "gemini_counttokens.json", "w"), indent=1, ensure_ascii=False)
