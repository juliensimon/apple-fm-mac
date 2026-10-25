#!/usr/bin/env python3
"""Long-context retrieval through the documented `fm serve` server: one fact (an access code) is placed at a given depth in filler text of
about N prompt tokens, then asked for. Six lengths, three depths, two needles per cell, temperature 0. Writes needle.csv and needle.json.
Run: fm serve --host 127.0.0.1 --port 18976   (in another terminal), then: python3 data/card_inputs/needle_test.py"""
import csv, json, os, random, time, urllib.request

os.chdir(os.path.dirname(os.path.abspath(__file__)))   # outputs are written beside this script

URL = "http://127.0.0.1:18976/v1/chat/completions"
rnd = random.Random(11)
NAMES = ["Alder", "Brooks", "Chen", "Duarte", "Eklund", "Farouk", "Gomez", "Haas", "Iyer", "Jansen", "Kovacs", "Lindqvist", "Moreau", "Novak", "Okafor", "Petrov"]
PLACES = ["the harbor office", "the north depot", "the city library", "the grain mill", "the river gauge", "the east warehouse", "the rail yard", "the school annex"]
THINGS = ["inspection", "delivery", "invoice", "survey", "maintenance visit", "audit", "shipment", "repair order"]
UNITS = ["crates", "meters", "liters", "pallets", "hours", "tons", "boxes", "sheets"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


def filler_sentence():
    return (f"On {rnd.choice(DAYS)}, {rnd.choice(NAMES)} filed report {rnd.randint(100, 9999)} about the {rnd.choice(THINGS)} at {rnd.choice(PLACES)}; "
            f"the count was {rnd.randint(11, 989)} {rnd.choice(UNITS)}.")


def ask(prompt):
    body = json.dumps({"model": "system", "messages": [{"role": "user", "content": prompt}], "stream": False, "temperature": 0}).encode()
    t = time.perf_counter()
    try:
        r = json.load(urllib.request.urlopen(urllib.request.Request(URL, body, {"Content-Type": "application/json"}), timeout=180))
        return r["choices"][0]["message"]["content"], r["usage"]["prompt_tokens"], time.perf_counter() - t, None
    except urllib.error.HTTPError as e:
        return "", None, time.perf_counter() - t, f"HTTP {e.code} {e.read().decode()[:120]}"
    except Exception as e:
        return "", None, time.perf_counter() - t, str(e)[:120]


# one filler sentence is about 30 tokens; calibrate with the first request of each cell by the usage numbers
TARGETS = [1000, 2000, 3500, 5000, 6500, 7500]
DEPTHS = [0.05, 0.5, 0.95]
rows = []
for target in TARGETS:
    for depth in DEPTHS:
        for trial in range(2):
            code = f"{rnd.choice(['BLUE', 'RED', 'GREEN', 'GOLD', 'GREY', 'TEAL'])}-{rnd.randint(1000, 9999)}"
            vault = rnd.randint(2, 9)
            needle = f"The access code for vault {vault} is {code}."
            n_sent = max(5, int((target - 90) / 30.5))
            sents = [filler_sentence() for _ in range(n_sent)]
            sents.insert(int(depth * n_sent), needle)
            prompt = " ".join(sents) + f"\n\nQuestion: what is the access code for vault {vault}? Answer with the code only."
            text, used, secs, err = ask(prompt)
            ok = code.lower() in text.lower()
            rows.append({"target_tokens": target, "prompt_tokens": used, "depth": depth, "trial": trial, "correct": int(ok), "answer": text.strip()[:80], "gold": code, "seconds": round(secs, 1), "error": err or ""})
            print(f"target {target:5d}  prompt_tokens {used}  depth {depth:4.2f}  trial {trial}  correct {int(ok)}  answer {text.strip()[:40]!r}  {secs:.1f}s  {err or ''}", flush=True)

with open("needle.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
json.dump(rows, open("needle.json", "w"), indent=1)
ok = sum(r["correct"] for r in rows)
print(f"overall {ok}/{len(rows)}")
for t in TARGETS:
    sub = [r for r in rows if r["target_tokens"] == t]
    print(t, "->", sum(r["correct"] for r in sub), "/", len(sub))
