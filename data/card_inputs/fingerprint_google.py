#!/usr/bin/env python3
"""Does the match hold for other Google tokenizers? Same 429 strings and Apple counts as fingerprint.py, against the Gemma 3n and Gemma 4 tokenizers
(Gemma 3 is the control). Writes fingerprint_google.json.
It reads corpus.json, which is not in this repository (170 of its strings are private); see data/tokenizer_test/ and
scripts/tokenizer_test.py. Run (with corpus.json present): uv run --with tokenizers --with numpy python data/card_inputs/fingerprint_google.py"""
import json
import os
import numpy as np
from tokenizers import Tokenizer

os.chdir(os.path.dirname(os.path.abspath(__file__)))   # the paths below are relative to this folder
cats = json.load(open("corpus.json")); apple = json.load(open("apple_counts.json"))
CANDS = [("Gemma 3 (control)", "unsloth/gemma-3-4b-it"), ("Gemma 3n E4B", "unsloth/gemma-3n-E4B-it"), ("Gemma 3n E2B", "unsloth/gemma-3n-E2B-it"),
         ("Gemma 4 E4B", "unsloth/gemma-4-E4B-it-unsloth-bnb-4bit"), ("Gemma 4 E2B", "unsloth/gemma-4-E2B-it-unsloth-bnb-4bit"),
         ("Gemma 4 26B-A4B", "unsloth/gemma-4-26B-A4B-it-NVFP4")]
res = {}
for name, repo in CANDS:
    try:
        t = Tokenizer.from_pretrained(repo)
    except Exception as e:
        print("skip", name, repo, str(e)[:100]); continue
    a_all, b_all = [], []
    for cat, items in cats.items():
        a_all += list(apple[cat]); b_all += [len(t.encode(s, add_special_tokens=False).ids) for s in items]
    a, b = np.array(a_all, float), np.array(b_all, float)
    res[name] = {"repo": repo, "vocab": t.get_vocab_size(), "exact": float(np.mean(a == b)), "within1": float(np.mean(np.abs(a - b) <= 1)), "mae": float(np.mean(np.abs(a - b)))}
    print(f"{name:20s} vocab {t.get_vocab_size():7d}  exact {res[name]['exact']*100:5.1f}%  within1 {res[name]['within1']*100:5.1f}%  mae {res[name]['mae']:.2f}  ({repo})")
json.dump(res, open("fingerprint_google.json", "w"), indent=1)
