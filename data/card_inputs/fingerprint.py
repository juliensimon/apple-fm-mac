# The 429 strings counted by ten public tokenizers against Apple's counts (REPORT 27.1). As run on 2026-10-24.
# It reads corpus.json, which is not in this repository (170 of its strings are private). The per-string counts it worked from
# are in data/tokenizer_test/counts_all_429.csv; scripts/check_numbers.py recomputes the shares from that file, and
# scripts/tokenizer_test.py runs the same test on any strings.
# Run (with corpus.json present): uv run --with tokenizers --with tiktoken --with numpy python data/card_inputs/fingerprint.py
import json, math, os, sys
import numpy as np
from tokenizers import Tokenizer
os.chdir(os.path.dirname(os.path.abspath(__file__)))   # the paths below are relative to this folder
cats = json.load(open("corpus.json")); apple = json.load(open("apple_counts.json"))
CANDS = [("gpt2 (50k)", "openai-community/gpt2"), ("Phi-3.5 mini (32k)", "microsoft/Phi-3.5-mini-instruct"), ("Llama 3.1 (128k)", "NousResearch/Meta-Llama-3.1-8B"),
         ("Mistral Nemo (131k)", "mistralai/Mistral-Nemo-Instruct-2407"), ("DeepSeek V3 (129k)", "deepseek-ai/DeepSeek-V3"), ("Qwen 2.5 (151k)", "Qwen/Qwen2.5-0.5B"),
         ("Gemma 2 (256k)", "unsloth/gemma-2-2b"), ("Gemma 3 (262k)", "unsloth/gemma-3-4b-it")]
toks = {}
for name, repo in CANDS:
    try:
        toks[name] = Tokenizer.from_pretrained(repo); print("loaded", name, "vocab", toks[name].get_vocab_size(), flush=True)
    except Exception as e: print("skip", name, str(e)[:90], flush=True)
try:
    import tiktoken
    for n, e in (("GPT-4o o200k (200k)", "o200k_base"), ("GPT-4 cl100k (100k)", "cl100k_base")):
        enc = tiktoken.get_encoding(e); toks[n] = enc
except Exception as e: print("tiktoken skip", str(e)[:80])
def count(t, s):
    if hasattr(t, "encode_ordinary"): return len(t.encode_ordinary(s))
    return len(t.encode(s, add_special_tokens=False).ids)
res = {}
for name, t in toks.items():
    per = {}; allA = []; allB = []
    for cat, items in cats.items():
        a = np.array([x for x in apple[cat]], float); b = np.array([count(t, s) for s in items], float)
        per[cat] = {"exact": float(np.mean(a == b)), "mae": float(np.mean(np.abs(a - b))), "ratio": float(np.sum(a) / np.sum(b))}
        allA += list(a); allB += list(b)
    allA, allB = np.array(allA), np.array(allB)
    res[name] = {"exact": float(np.mean(allA == allB)), "within1": float(np.mean(np.abs(allA - allB) <= 1)), "mae": float(np.mean(np.abs(allA - allB))), "ratio": float(allA.sum() / allB.sum()), "per": per}
json.dump(res, open("fingerprint.json", "w"), indent=1)
print()
print(f"{'tokenizer':24s} {'exact':>7s} {'within 1':>9s} {'mean abs diff':>14s} {'apple/other':>12s}   exact match by category (prose, report, multi, code, num, rare)")
for n, r in sorted(res.items(), key=lambda kv: -kv[1]["exact"]):
    p = r["per"]; print(f"{n:24s} {r['exact']*100:6.1f}% {r['within1']*100:8.1f}% {r['mae']:14.2f} {r['ratio']:12.3f}   " + " ".join(f"{p[c]['exact']*100:4.0f}" for c in cats))
