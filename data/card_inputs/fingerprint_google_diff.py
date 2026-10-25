#!/usr/bin/env python3
"""Which strings separate Gemma 4's tokenizer from Apple's counts? Prints the strings, the counts and the Gemma 3 tokens versus the Gemma 4 tokens.
It reads corpus.json, which is not in this repository; the four strings it found are all public and are in fingerprint_google_diff.json.
Run (with corpus.json present): uv run --with tokenizers python data/card_inputs/fingerprint_google_diff.py"""
import json
import os
from tokenizers import Tokenizer

os.chdir(os.path.dirname(os.path.abspath(__file__)))   # the paths below are relative to this folder
cats = json.load(open("corpus.json")); apple = json.load(open("apple_counts.json"))
g3 = Tokenizer.from_pretrained("unsloth/gemma-3-4b-it"); g4 = Tokenizer.from_pretrained("unsloth/gemma-4-E4B-it-unsloth-bnb-4bit")
rows = []
for cat, items in cats.items():
    for s, a in zip(items, apple[cat]):
        e3 = g3.encode(s, add_special_tokens=False); e4 = g4.encode(s, add_special_tokens=False)
        if len(e4.ids) != a:
            rows.append({"category": cat, "string": s, "apple": a, "gemma3": len(e3.ids), "gemma4": len(e4.ids), "gemma3_tokens": e3.tokens, "gemma4_tokens": e4.tokens})
for r in rows:
    print(json.dumps(r, ensure_ascii=False)[:900])
json.dump(rows, open("fingerprint_google_diff.json", "w"), indent=1, ensure_ascii=False)
print(len(rows), "strings differ between Apple and Gemma 4")
