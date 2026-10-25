#!/usr/bin/env python3
"""Small spot checks of the on-device model through the documented `fm serve` API.
GSM8K (100 random test problems, zero-shot with step-by-step reasoning) and MMLU (200 random test questions, zero-shot, letter answer).
Greedy-like decoding (temperature 0). One run. These are sanity checks, not benchmark submissions.
Run: fm serve --host 127.0.0.1 --port 18976   (in another terminal), then:
     uv run --with pandas --with pyarrow --with huggingface_hub python data/card_inputs/evals.py   (writes evals.json here)
The run of 2026-10-24 read local copies of the two test files; this copy downloads the same files from the Hugging Face Hub
and checks them against the SHA-256 in evals_data_sha256.txt, so the seeded draw picks the same 100 + 200 items."""
import hashlib, json, math, os, random, re, sys, time, urllib.request
import pandas as pd
from huggingface_hub import hf_hub_download

os.chdir(os.path.dirname(os.path.abspath(__file__)))   # evals.json is written beside this script
URL = "http://127.0.0.1:18976/v1/chat/completions"
SEED = 7
SHA = {"gsm8k": "ee7b8da9e381df27b9e3f7758a159ab2bdaa4dbaa910546cbbc47e0cb44e4f59", "mmlu": "74a41822ce7d3def56e1682f958469c04642a5336a5ce912fa375fdb90fb25d7"}


def data(name, repo, path):
    p = hf_hub_download(repo, path, repo_type="dataset")
    assert hashlib.sha256(open(p, "rb").read()).hexdigest() == SHA[name], f"{name} file differs from the one the run used"
    return pd.read_parquet(p)


def chat(prompt, system=None):
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    body = json.dumps({"model": "system", "messages": msgs, "stream": False, "temperature": 0}).encode()
    t = time.perf_counter()
    try:
        r = json.load(urllib.request.urlopen(urllib.request.Request(URL, body, {"Content-Type": "application/json"}), timeout=180))
        return r["choices"][0]["message"]["content"], r.get("usage", {}), time.perf_counter() - t, None
    except urllib.error.HTTPError as e:
        return "", {}, time.perf_counter() - t, f"HTTP {e.code} {e.read().decode()[:120]}"
    except Exception as e:
        return "", {}, time.perf_counter() - t, str(e)[:120]


def wilson(k, n, z=1.96):
    if n == 0: return (0, 0)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


out = {"gsm8k": [], "mmlu": []}
g = data("gsm8k", "openai/gsm8k", "main/test-00000-of-00001.parquet"); rnd = random.Random(SEED)
idx = rnd.sample(range(len(g)), 100)
ok = 0
for n, i in enumerate(idx):
    q, a = g.question[i], g.answer[i]; gold = a.split("####")[-1].strip().replace(",", "")
    text, usage, dt, err = chat(f"Solve the following math problem step by step. At the end, write the final number on its own line as 'Answer: <number>'.\n\n{q}")
    m = re.findall(r"Answer:\s*\$?\s*(-?[\d,]*\.?\d+)", text); pred = m[-1].replace(",", "") if m else (re.findall(r"-?[\d,]*\.?\d+", text) or [""])[-1].replace(",", "")
    try: right = abs(float(pred) - float(gold)) < 1e-6
    except ValueError: right = False
    ok += right; out["gsm8k"].append({"i": int(i), "gold": gold, "pred": pred, "right": bool(right), "seconds": round(dt, 2), "out_tokens": usage.get("completion_tokens"), "error": err})
    if n % 10 == 9: print(f"gsm8k {n+1}/100  correct so far {ok}", flush=True)
lo, hi = wilson(ok, 100); print(f"GSM8K (n=100): {ok}% correct  95% CI {lo*100:.0f} to {hi*100:.0f}", flush=True)

m_ = data("mmlu", "cais/mmlu", "all/test-00000-of-00001.parquet"); idx = rnd.sample(range(len(m_)), 200); ok = 0; errs = 0
for n, i in enumerate(idx):
    r = m_.iloc[i]; ch = list(r.choices)
    prompt = f"The following is a multiple choice question about {r.subject.replace('_', ' ')}. Reply with only the letter of the correct answer.\n\n{r.question}\nA. {ch[0]}\nB. {ch[1]}\nC. {ch[2]}\nD. {ch[3]}\nAnswer:"
    text, usage, dt, err = chat(prompt)
    mm = re.search(r"\b([ABCD])\b", text.strip()[:12]); pred = mm.group(1) if mm else ""
    right = pred == "ABCD"[int(r.answer)]; ok += right; errs += bool(err)
    out["mmlu"].append({"i": int(i), "subject": r.subject, "gold": "ABCD"[int(r.answer)], "pred": pred, "right": bool(right), "seconds": round(dt, 2), "error": err})
    if n % 25 == 24: print(f"mmlu {n+1}/200  correct so far {ok}  errors {errs}", flush=True)
lo, hi = wilson(ok, 200); print(f"MMLU (n=200): {ok/2:.1f}% correct  95% CI {lo*100:.1f} to {hi*100:.1f}  (errors/refusals: {errs})", flush=True)
json.dump(out, open("evals.json", "w"), indent=1)
print("done")
