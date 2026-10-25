#!/usr/bin/env python3
"""The workload for the energy run (run by run_energy.sh as the normal user, while `powermetrics` runs as root).
Written 2026-10-24, before any result. Question: how much energy does each model use per solved grade-school math problem on this Mac?
Same 20 GSM8K problems (the first 20 of the 100 Apple was scored on), same prompt, same client, temperature 0, for Apple's model through
`fm serve` and for the three 8-bit open builds through `mlx_lm.server`. Each phase is preceded by a model warm-up outside the timed window.
My thresholds, not a standard:
  H3: Apple's model uses less energy per solved problem than each open build. Holds if its joules per solved problem are below all three.
      Fails if any open build uses less.
Writes phases.json, or phases_4bit.json with ENERGY_TAG=_4bit (epoch start and end of each timed phase, the solved count) next to this script.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd
from huggingface_hub import hf_hub_download

HERE = Path(__file__).resolve().parent
EVALS = HERE.parents[3] / "docs" / "apple-fm" / "data" / "card_inputs" / "evals.json"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
BASELINE_S = int(os.environ.get("ENERGY_BASELINE_S", "30"))   # the real run keeps 30; a test run may shorten it
ONLY = os.environ.get("ENERGY_ONLY")                          # a test run may name one model slug
SHA = "ee7b8da9e381df27b9e3f7758a159ab2bdaa4dbaa910546cbbc47e0cb44e4f59"
ALL_MODELS = [("apple", None, 18977), ("gemma3-4b-8bit", "mlx-community/gemma-3-4b-it-8bit", 18978),
          ("gemma4-e4b-8bit", "mlx-community/gemma-4-e4b-it-8bit", 18979), ("qwen3-4b-8bit", "mlx-community/Qwen3-4B-Instruct-2507-8bit", 18980)]
TAG = os.environ.get("ENERGY_TAG", "")                       # "" for the 8-bit set of 2026-10-25; "_4bit" for the 4-bit set
if TAG == "_4bit":   # added 2026-10-25 after the story meeting: the falsifier names a 4-bit build; Apple's model runs again as a repeat
    ALL_MODELS = [("apple", None, 18977), ("gemma3-4b-4bit", "mlx-community/gemma-3-4b-it-4bit", 18981),
                  ("gemma4-e4b-4bit", "mlx-community/gemma-4-e4b-it-4bit", 18982), ("qwen3-4b-4bit", "mlx-community/Qwen3-4B-Instruct-2507-4bit", 18983)]
MODELS = [m for m in ALL_MODELS if not ONLY or m[0] == ONLY]

p = hf_hub_download("openai/gsm8k", "main/test-00000-of-00001.parquet", repo_type="dataset")
assert hashlib.sha256(open(p, "rb").read()).hexdigest() == SHA
g = pd.read_parquet(p)
items = json.load(open(EVALS))["gsm8k"][:N]


def chat(port, model, prompt, max_tokens=None, timeout=900):
    body = {"model": model or "system", "messages": [{"role": "user", "content": prompt}], "stream": False, "temperature": 0}
    if max_tokens:
        body["max_tokens"] = max_tokens
    r = json.load(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"}), timeout=timeout))
    return r["choices"][0]["message"]["content"]


def wait_ready(port, tries=300):
    for _ in range(tries):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=2); return
        except Exception:
            time.sleep(2)
    raise SystemExit(f"server on {port} did not answer")


phases = {"n_problems": N, "date": time.strftime("%Y-%m-%d"), "phases": []}
time.sleep(BASELINE_S)                                # baseline: idle, nothing running
phases["phases"].append({"name": "baseline_idle", "start": time.time() - BASELINE_S, "end": time.time()})
for slug, repo, port in MODELS:
    cmd = (["fm", "serve", "--port", str(port)] if repo is None else
           ["uv", "run", "--quiet", "--no-project", "--with", "mlx-lm", "mlx_lm.server", "--model", repo, "--port", str(port), "--temp", "0.0", "--chat-template-args", json.dumps({"enable_thinking": False})])
    srv = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_ready(port)
        chat(port, repo, "Say hi in three words.", 16)   # warm-up: loads the model, outside the timed window
        time.sleep(15)                                    # let power settle
        t0 = time.time(); solved = 0; errors = []
        for a in items:
            i = a["i"]; q, ans = g.question[i], g.answer[i]; gold = ans.split("####")[-1].strip().replace(",", "")
            try:
                text = chat(port, repo, f"Solve the following math problem step by step. At the end, write the final number on its own line as 'Answer: <number>'.\n\n{q}", None if repo is None else 1000)
            except urllib.error.HTTPError as e:   # a guardrail refusal comes back as HTTP 500; it counts as unsolved, as in the scoring runs
                text = ""; errors.append({"i": i, "http": e.code, "body": e.read()[:300].decode("utf-8", "ignore")})
            except Exception as e:
                text = ""; errors.append({"i": i, "error": str(e)[:300]})
            m = re.findall(r"Answer:\s*\$?\s*(-?[\d,]*\.?\d+)", text); pred = m[-1].replace(",", "") if m else (re.findall(r"-?[\d,]*\.?\d+", text) or [""])[-1].replace(",", "")
            try: solved += abs(float(pred) - float(gold)) < 1e-6
            except ValueError: pass
        t1 = time.time()
        phases["phases"].append({"name": slug, "start": t0, "end": t1, "solved": int(solved), "problems": N, "errors": errors})
        print(slug, "solved", solved, "of", N, "in", round(t1 - t0, 1), "s;", len(errors), "request errors", flush=True)
    finally:
        srv.terminate()
        try: srv.wait(30)
        except Exception: srv.kill()
    time.sleep(25)                                        # cool-down and idle between phases
    phases["phases"].append({"name": f"idle_after_{slug}", "start": time.time() - 25, "end": time.time()})
json.dump(phases, open(HERE / f"phases{TAG}.json", "w"), indent=1)
print("workload done")
