#!/usr/bin/env python3
"""The eight MMLU questions whose open-model replies were cut by the 8-token cap (they began to reason instead of giving a letter): rerun with a
2,048-token cap, same prompt, temperature 0, and read the final answer from the end of the reply.
Run: uv run --quiet --no-project --with mlx-lm --with pandas --with pyarrow --with huggingface_hub python data/compare/mmlu_uncapped.py
"""
import hashlib
import json
import re
from pathlib import Path

import pandas as pd
from huggingface_hub import hf_hub_download
from mlx_lm import generate, load
from mlx_lm.sample_utils import make_sampler

HERE = Path(__file__).resolve().parent
SHA = "74a41822ce7d3def56e1682f958469c04642a5336a5ce912fa375fdb90fb25d7"
CUT = {"mlx-community/Qwen3-4B-Instruct-2507-8bit": [2243, 2478, 1152, 4337, 4278, 4246], "mlx-community/gemma-4-e4b-it-8bit": [457, 4246]}

p = hf_hub_download("cais/mmlu", "all/test-00000-of-00001.parquet", repo_type="dataset")
assert hashlib.sha256(open(p, "rb").read()).hexdigest() == SHA
m_ = pd.read_parquet(p)
sampler = make_sampler(temp=0.0)
out = {}
for repo, items in CUT.items():
    model, tok = load(repo)
    for i in items:
        r = m_.iloc[i]; ch = list(r.choices)
        prompt = (f"The following is a multiple choice question about {r.subject.replace('_', ' ')}. Reply with only the letter of the correct answer.\n\n"
                  f"{r.question}\nA. {ch[0]}\nB. {ch[1]}\nC. {ch[2]}\nD. {ch[3]}\nAnswer:")
        text = tok.apply_chat_template([{"role": "user", "content": prompt}], add_generation_prompt=True, tokenize=False, enable_thinking=False)
        reply = generate(model, tok, prompt=text, max_tokens=2048, sampler=sampler, verbose=False)
        tail = reply.strip()[-300:]
        found = re.findall(r"(?:answer is|correct answer is|Answer:)\s*\**\(?([ABCD])\b", reply, re.I) or re.findall(r"\*\*([ABCD])\*\*", reply) or re.findall(r"\b([ABCD])\b", tail)
        pred = found[-1].upper() if found else ""
        gold = "ABCD"[int(r.answer)]
        out[f"{repo}:{i}"] = {"subject": r.subject, "gold": gold, "pred": pred, "right": pred == gold, "tokens": len(tok.encode(reply)), "tail": tail}
        print(f"{repo.split('/')[1][:22]:22s} item {i:5d} gold {gold} pred {pred or '-'} {'RIGHT' if pred == gold else 'wrong'}  ({len(tok.encode(reply))} tokens)  ...{tail[-120:]!r}", flush=True)
json.dump(out, open(HERE / "mmlu_uncapped.json", "w"), indent=1, ensure_ascii=False)
for repo in CUT:
    rows = [v for k, v in out.items() if k.startswith(repo)]
    print(repo, "right", sum(v["right"] for v in rows), "of", len(rows))
