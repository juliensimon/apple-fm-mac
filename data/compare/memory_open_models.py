#!/usr/bin/env python3
"""Memory the three open 8-bit builds need on this Mac, to set beside Apple's model (1.3 GiB held between requests, REPORT 12 and 28.1).
Written 2026-10-24 to price the open builds' side of the memory comparison. For each build: GPU memory in use after loading (the weights),
and the peak while writing a 300-token reply to one of the GSM8K prompts. MLX counts only its own allocations; Apple's figure comes from
`footprint` and `vmmap`, so the two are the same kind of number (memory the model holds) but not the same instrument.
Run: uv run --quiet --no-project --with mlx-lm python data/compare/memory_open_models.py
"""
import json
import time
from pathlib import Path

import mlx.core as mx
from mlx_lm import generate, load
from mlx_lm.sample_utils import make_sampler

HERE = Path(__file__).resolve().parent
REPOS = ["mlx-community/gemma-3-4b-it-8bit", "mlx-community/gemma-4-e4b-it-8bit", "mlx-community/Qwen3-4B-Instruct-2507-8bit"]
PROMPT = ("Solve the following math problem step by step. At the end, write the final number on its own line as 'Answer: <number>'.\n\n"
          "A robe takes 2 bolts of blue fiber and half that much white fiber. How many bolts in total does it take?")


def gib(b):
    return round(b / 2**30, 2)


def active():
    return mx.get_active_memory() if hasattr(mx, "get_active_memory") else mx.metal.get_active_memory()


def peak():
    return mx.get_peak_memory() if hasattr(mx, "get_peak_memory") else mx.metal.get_peak_memory()


def reset():
    (mx.reset_peak_memory if hasattr(mx, "reset_peak_memory") else mx.metal.reset_peak_memory)()


out = {"date": time.strftime("%Y-%m-%d"), "note": "GiB = 2^30 bytes; MLX allocations only", "models": {}}
for repo in REPOS:
    model, tok = load(repo)
    mx.eval(model.parameters())
    after_load = active()
    reset()
    text = tok.apply_chat_template([{"role": "user", "content": PROMPT}], add_generation_prompt=True, tokenize=False, enable_thinking=False)
    reply = generate(model, tok, prompt=text, max_tokens=300, sampler=make_sampler(temp=0.0), verbose=False)
    out["models"][repo] = {"after_load_gib": gib(after_load), "peak_during_reply_gib": gib(peak()), "reply_tokens": len(tok.encode(reply))}
    print(repo, out["models"][repo], flush=True)
    del model, tok
    mx.clear_cache() if hasattr(mx, "clear_cache") else mx.metal.clear_cache()
json.dump(out, open(HERE / "memory_open_models.json", "w"), indent=1)
