#!/usr/bin/env python3
"""Paired comparison of Core Advanced with each open model on the same questions: counts of both right, only one right, and an exact McNemar p-value."""
import json, math, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
apple = json.load(open(HERE.parent / "card_inputs" / "evals.json"))   # Apple's run through fm serve


def mcnemar_p(b, c):
    n = b + c
    if n == 0: return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


for path in sorted(HERE.glob("results_*.json")):
    r = json.load(open(path))
    if r["slug"] == "apple" or "gsm8k" not in r: continue
    print(f"== {r['slug']} ({r['repo']})")
    for bench in ("gsm8k", "mmlu"):
        a = {x["i"]: x["right"] for x in apple[bench]}; o = {x["i"]: x["right"] for x in r[bench]["rows"]}
        both = sum(1 for i in a if a[i] and o[i]); only_a = sum(1 for i in a if a[i] and not o[i]); only_o = sum(1 for i in a if o[i] and not a[i]); none = sum(1 for i in a if not a[i] and not o[i])
        print(f"  {bench}: apple {sum(a.values())}/{len(a)}  open {sum(o.values())}/{len(o)}  both right {both}, only Apple {only_a}, only open {only_o}, both wrong {none}, exact McNemar p = {mcnemar_p(only_a, only_o):.4g}")
