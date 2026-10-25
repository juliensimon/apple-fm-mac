#!/usr/bin/env python3
"""Asks Apple's model again the three GSM8K problems whose answers parsed as 0 in the main run (test items 1097, 1140 and 953),
same prompt, through `fm serve` at temperature 0, and keeps the head and tail of each reply. Writes recheck_gsm.json beside this script.
Run: fm serve --host 127.0.0.1 --port 18977   (in another terminal; this recheck used a second port), then:
     uv run --with pandas --with pyarrow --with huggingface_hub python data/compare/recheck_gsm.py"""
import json, re, urllib.request, hashlib, pandas as pd
from pathlib import Path
from huggingface_hub import hf_hub_download
HERE = Path(__file__).resolve().parent
p = hf_hub_download("openai/gsm8k", "main/test-00000-of-00001.parquet", repo_type="dataset")
assert hashlib.sha256(open(p, "rb").read()).hexdigest() == "ee7b8da9e381df27b9e3f7758a159ab2bdaa4dbaa910546cbbc47e0cb44e4f59"
g = pd.read_parquet(p)
def chat(prompt):
    body = json.dumps({"model": "system", "messages": [{"role": "user", "content": prompt}], "stream": False, "temperature": 0}).encode()
    req = urllib.request.Request("http://127.0.0.1:18977/v1/chat/completions", data=body, headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=300))["choices"][0]["message"]["content"]
out = {}
for i in (1097, 1140, 953):
    q, ans = g.question[i], g.answer[i]; gold = ans.split("####")[-1].strip().replace(",", "")
    text = chat(f"Solve the following math problem step by step. At the end, write the final number on its own line as 'Answer: <number>'.\n\n{q}")
    m = re.findall(r"Answer:\s*\$?\s*(-?[\d,]*\.?\d+)", text); pred = m[-1].replace(",", "") if m else (re.findall(r"-?[\d,]*\.?\d+", text) or [""])[-1].replace(",", "")
    out[i] = {"gold": gold, "pred": pred, "length": len(text), "head": text[:200], "tail": text[-260:]}
    print(i, "gold", gold, "pred", repr(pred), "chars", len(text)); print("   TAIL:", repr(text[-260:])); print()
json.dump(out, open(HERE / "recheck_gsm.json", "w"), indent=1)
