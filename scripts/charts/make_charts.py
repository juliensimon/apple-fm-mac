#!/usr/bin/env python3
"""The tokenizer chart (plots/tokenizer-match.png) from data/tokenizer_fingerprint.csv and data/fingerprint_google.json.
Run: uv run --quiet --with matplotlib --with numpy python scripts/charts/make_charts.py"""
import csv
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]                      # repository root
DATA = ROOT / "data"
sys.path.insert(0, str(HERE))
from brand import Sheet, ACCENT             # noqa: E402

DAY = date(2026, 10, 26)                    # the sheet number follows the publication date; update at publication

rows = list(csv.DictReader(open(DATA / "tokenizer_fingerprint.csv")))
nice = {"gpt2 (50k)": "GPT-2 (50k)"}
items = [(nice.get(r["tokenizer"], r["tokenizer"]), float(r["exact_match_pct"])) for r in rows]
import json
g = json.load(open(DATA / "fingerprint_google.json"))      # the same 429 strings against Gemma 3n and Gemma 4 (fingerprint_google.py)
for name, label in (("Gemma 3n E4B", "Gemma 3n (262k)"), ("Gemma 4 E4B", "Gemma 4 (262k)")):
    items.append((label, round(g[name]["exact"] * 100, 1)))
items.sort(key=lambda kv: -kv[1])
sheet = Sheet("substack", "Gemma 3 matches Apple's token counts on 429 of 429 strings",
              "Share of 429 test strings where a public tokenizer gives exactly Apple's count",
              "Author's measurement through Apple's fm count-tokens, macOS 27.0.1 (26A434), 2026-10-24. Data: data/tokenizer_fingerprint.csv and data/fingerprint_google.json",
              day=DAY)
sheet.ranking(items, fmt=lambda v: f"{v:.1f}%", highlight={"Gemma 3 (262k)": ACCENT})
print(sheet.save(ROOT / "plots" / "tokenizer-match.png"))
