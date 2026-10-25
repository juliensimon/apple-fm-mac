#!/usr/bin/env python3
"""Behind one API. The earlier open-model runs called mlx-lm in process; Apple's model was called through `fm serve` with the client in
data/card_inputs/evals.py. This run puts each open 8-bit build behind a local server (mlx_lm.server) and calls it with the
same client code, the same prompts, the same item indices, the same scoring and temperature 0.
Written 2026-10-24, BEFORE any result. My thresholds, not a standard:
  Holds if each model's GSM8K and MMLU counts stay within 3 of the in-process run (results_<slug>.json). Fails if any count moves by more than 3.
Also records `footprint` (the same macOS tool behind the 1.3 GiB figure for Apple's model) for the server process after the first reply
and after the last.
Run: uv run --quiet --no-project --with pandas --with pyarrow --with huggingface_hub python data/compare/server_rerun.py <hf repo> <slug> <port>
"""
import hashlib
import json
import math
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd
from huggingface_hub import hf_hub_download

HERE = Path(__file__).resolve().parent
EVALS = HERE.parent / "card_inputs" / "evals.json"   # Apple's run: item indices and results
SHA = {"gsm8k": "ee7b8da9e381df27b9e3f7758a159ab2bdaa4dbaa910546cbbc47e0cb44e4f59", "mmlu": "74a41822ce7d3def56e1682f958469c04642a5336a5ce912fa375fdb90fb25d7"}
repo, slug, port = sys.argv[1], sys.argv[2], int(sys.argv[3])
URL = f"http://127.0.0.1:{port}/v1/chat/completions"


def data(name, ds, path):
    p = hf_hub_download(ds, path, repo_type="dataset")
    assert hashlib.sha256(open(p, "rb").read()).hexdigest() == SHA[name]
    return pd.read_parquet(p)


def chat(prompt, max_tokens):
    body = json.dumps({"model": repo, "messages": [{"role": "user", "content": prompt}], "stream": False, "temperature": 0, "max_tokens": max_tokens}).encode()
    t = time.perf_counter()
    try:
        r = json.load(urllib.request.urlopen(urllib.request.Request(URL, body, {"Content-Type": "application/json"}), timeout=600))
        return r["choices"][0]["message"]["content"], r.get("usage", {}), time.perf_counter() - t, None
    except Exception as e:
        return "", {}, time.perf_counter() - t, str(e)[:120]


def footprint(pid):
    out = subprocess.run(["footprint", str(pid)], capture_output=True, text=True).stdout
    m = re.search(r"Footprint:\s*([\d.]+)\s*(KB|MB|GB)", out)
    mib = None
    if m:
        v = float(m.group(1)); mib = v / 1024 if m.group(2) == "KB" else v if m.group(2) == "MB" else v * 1024
    return {"footprint_mib": mib and round(mib, 1), "text": out[:1800]}


srv = subprocess.Popen(["uv", "run", "--quiet", "--no-project", "--with", "mlx-lm", "mlx_lm.server", "--model", repo, "--port", str(port), "--temp", "0.0",
                        "--chat-template-args", json.dumps({"enable_thinking": False})], stdout=open(HERE / f"server_{slug}.log", "w"), stderr=subprocess.STDOUT)
try:
    for _ in range(240):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=2); break
        except Exception:
            time.sleep(2)
    pid = int(subprocess.run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"], capture_output=True, text=True).stdout.split()[0])
    apple = json.load(open(EVALS))
    g = data("gsm8k", "openai/gsm8k", "main/test-00000-of-00001.parquet")
    m_ = data("mmlu", "cais/mmlu", "all/test-00000-of-00001.parquet")
    res = {"repo": repo, "slug": slug, "date": time.strftime("%Y-%m-%d"), "api": "mlx_lm.server /v1/chat/completions, client as evals.py", "gsm8k": [], "mmlu": []}
    ok = 0
    for n, a in enumerate(apple["gsm8k"]):
        i = a["i"]; q, ans = g.question[i], g.answer[i]; gold = ans.split("####")[-1].strip().replace(",", "")
        text, usage, dt, err = chat(f"Solve the following math problem step by step. At the end, write the final number on its own line as 'Answer: <number>'.\n\n{q}", 1000)
        m = re.findall(r"Answer:\s*\$?\s*(-?[\d,]*\.?\d+)", text); pred = m[-1].replace(",", "") if m else (re.findall(r"-?[\d,]*\.?\d+", text) or [""])[-1].replace(",", "")
        try: right = abs(float(pred) - float(gold)) < 1e-6
        except ValueError: right = False
        ok += right; res["gsm8k"].append({"i": i, "gold": gold, "pred": pred, "right": bool(right), "seconds": round(dt, 2), "out_tokens": usage.get("completion_tokens"), "error": err})
        if n == 0: res["footprint_after_first_reply"] = footprint(pid)
        if n % 20 == 19: print(slug, f"gsm8k {n + 1}/100 correct so far {ok}", flush=True)
    ok2 = 0
    for n, a in enumerate(apple["mmlu"]):
        i = a["i"]; r = m_.iloc[i]; ch = list(r.choices)
        prompt = (f"The following is a multiple choice question about {r.subject.replace('_', ' ')}. Reply with only the letter of the correct answer.\n\n"
                  f"{r.question}\nA. {ch[0]}\nB. {ch[1]}\nC. {ch[2]}\nD. {ch[3]}\nAnswer:")
        text, usage, dt, err = chat(prompt, 8)
        mm = re.search(r"\b([ABCD])\b", text.strip()[:12]); pred = mm.group(1) if mm else ""
        right = pred == "ABCD"[int(r.answer)]; ok2 += right
        res["mmlu"].append({"i": i, "subject": r.subject, "gold": "ABCD"[int(r.answer)], "pred": pred, "right": bool(right), "seconds": round(dt, 2), "error": err})
        if n % 50 == 49: print(slug, f"mmlu {n + 1}/200 correct so far {ok2}", flush=True)
    res["footprint_after_last_reply"] = footprint(pid)
    res["gsm8k_correct"], res["mmlu_correct"] = ok, ok2
    old = json.load(open(HERE / f"results_{slug}.json"))
    res["in_process_gsm8k_correct"], res["in_process_mmlu_correct"] = old["gsm8k"]["correct"], old["mmlu"]["correct"]
    oldg = {r["i"]: r["right"] for r in old["gsm8k"]["rows"]}; oldm = {r["i"]: r["right"] for r in old["mmlu"]["rows"]}
    res["gsm8k_items_that_changed"] = sum(1 for r in res["gsm8k"] if oldg.get(r["i"]) != r["right"])
    res["mmlu_items_that_changed"] = sum(1 for r in res["mmlu"] if oldm.get(r["i"]) != r["right"])
    json.dump(res, open(HERE / f"server_rerun_{slug}.json", "w"), indent=1, ensure_ascii=False)
    print(slug, "GSM8K", ok, "(in process", old["gsm8k"]["correct"], ") MMLU", ok2, "(in process", old["mmlu"]["correct"], ")  changed items", res["gsm8k_items_that_changed"], res["mmlu_items_that_changed"],
          " footprint MiB", res["footprint_after_first_reply"]["footprint_mib"], res["footprint_after_last_reply"]["footprint_mib"], flush=True)
finally:
    srv.terminate()
    try: srv.wait(30)
    except Exception: srv.kill()
