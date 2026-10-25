#!/usr/bin/env python3
"""Same questions, same prompts, same scorer, same Mac: open models run with MLX against Core Advanced (run earlier through `fm serve`).

Written on 2026-10-24 BEFORE any open-model run. My thresholds, not a standard:
  H1 (GSM8K and MMLU): Gemma 3 4B lands within 10 points of Core Advanced on the same 100 GSM8K problems and 200 MMLU questions.
     Holds if both gaps are under 10 points. Fails if either gap is 10 points or more.
  H2 (knowledge date): Core Advanced answers dated events like Gemma 3 4B does. Holds if its share of correct answers for events from
     September 2024 on is within 20 points of Gemma 3 4B's. Fails if it is 20 points or more above (a later data cutoff than Gemma 3's August 2024).
Run: uv run --quiet --no-project --with mlx-lm --with pandas --with pyarrow --with huggingface_hub python data/compare/compare_models.py <hf repo> <slug> [gsm8k mmlu dated]
Apple's side: evals.json (indices and results) and dated_events_apple.py."""
import hashlib, json, math, re, sys, time
from pathlib import Path

import pandas as pd
from huggingface_hub import hf_hub_download
from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler

HERE = Path(__file__).resolve().parent
EVALS = HERE.parent / "card_inputs" / "evals.json"   # Apple's run: item indices and results
SHA = {"gsm8k": "ee7b8da9e381df27b9e3f7758a159ab2bdaa4dbaa910546cbbc47e0cb44e4f59", "mmlu": "74a41822ce7d3def56e1682f958469c04642a5336a5ce912fa375fdb90fb25d7"}


def data(name, repo, path):
    p = hf_hub_download(repo, path, repo_type="dataset")
    assert hashlib.sha256(open(p, "rb").read()).hexdigest() == SHA[name], f"{name} file differs from the one Apple's run used"
    return pd.read_parquet(p)


def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return round(100 * (c - h) / d, 1), round(100 * (c + h) / d, 1)


repo, slug = sys.argv[1], sys.argv[2]
parts = sys.argv[3:] or ["gsm8k", "mmlu", "dated"]
apple = json.load(open(EVALS))
t0 = time.time(); model, tok = load(repo); print("loaded", repo, round(time.time() - t0, 1), "s", flush=True)
sampler = make_sampler(temp=0.0)


def ask(prompt, max_tokens):
    text = tok.apply_chat_template([{"role": "user", "content": prompt}], add_generation_prompt=True, tokenize=False, enable_thinking=False)  # Apple's model has no reasoning mode; Gemma 3 ignores the flag
    t = time.perf_counter()
    out = generate(model, tok, prompt=text, max_tokens=max_tokens, sampler=sampler, verbose=False)
    return out, time.perf_counter() - t, len(tok.encode(out))


res = {"repo": repo, "slug": slug, "date": time.strftime("%Y-%m-%d")}

if "gsm8k" in parts:
    g = data("gsm8k", "openai/gsm8k", "main/test-00000-of-00001.parquet"); rows = []; ok = 0
    for n, a in enumerate(apple["gsm8k"]):
        i = a["i"]; q, ans = g.question[i], g.answer[i]; gold = ans.split("####")[-1].strip().replace(",", "")
        text, secs, ntok = ask(f"Solve the following math problem step by step. At the end, write the final number on its own line as 'Answer: <number>'.\n\n{q}", 1000)
        m = re.findall(r"Answer:\s*\$?\s*(-?[\d,]*\.?\d+)", text); pred = m[-1].replace(",", "") if m else (re.findall(r"-?[\d,]*\.?\d+", text) or [""])[-1].replace(",", "")
        try: right = abs(float(pred) - float(gold)) < 1e-6
        except ValueError: right = False
        ok += right; rows.append({"i": i, "gold": gold, "pred": pred, "right": bool(right), "seconds": round(secs, 2), "out_tokens": ntok})
        if n % 20 == 19: print(f"gsm8k {n + 1}/100 correct so far {ok}", flush=True)
    res["gsm8k"] = {"n": len(rows), "correct": ok, "ci95": wilson(ok, len(rows)), "rows": rows}
    print("GSM8K", ok, "/", len(rows), res["gsm8k"]["ci95"], flush=True)

if "mmlu" in parts:
    m_ = data("mmlu", "cais/mmlu", "all/test-00000-of-00001.parquet"); rows = []; ok = 0
    for n, a in enumerate(apple["mmlu"]):
        i = a["i"]; r = m_.iloc[i]; ch = list(r.choices)
        text, secs, ntok = ask(f"The following is a multiple choice question about {r.subject.replace('_', ' ')}. Reply with only the letter of the correct answer.\n\n{r.question}\nA. {ch[0]}\nB. {ch[1]}\nC. {ch[2]}\nD. {ch[3]}\nAnswer:", 8)
        mm = re.search(r"\b([ABCD])\b", text.strip()[:12]); pred = mm.group(1) if mm else ""
        right = pred == "ABCD"[int(r.answer)]; ok += right
        rows.append({"i": i, "subject": r.subject, "gold": "ABCD"[int(r.answer)], "pred": pred, "right": bool(right), "reply": text.strip()[:40]})
        if n % 50 == 49: print(f"mmlu {n + 1}/200 correct so far {ok}", flush=True)
    res["mmlu"] = {"n": len(rows), "correct": ok, "ci95": wilson(ok, len(rows)), "unparsed": sum(1 for r in rows if not r["pred"]), "rows": rows}
    print("MMLU", ok, "/", len(rows), res["mmlu"]["ci95"], "unparsed", res["mmlu"]["unparsed"], flush=True)

if "dated" in parts:
    ev = json.load(open(HERE / "dated_events.json"))
    ABSTAIN = re.compile(r"don't know|do not know|not aware|no information|cannot|can't|as of my|knowledge cutoff|unable|unsure|no record|haven't|not sure|don't have", re.I)
    MODES = {"abstain": "Answer in one short sentence. If you do not know, reply 'I do not know'.", "guess": "Answer in one short sentence."}
    for mode, lead in MODES.items():
        rows = []
        for e in ev:
            text, secs, ntok = ask(f"{lead}\n\n{e['q']}", 60)
            status = "correct" if re.search(e["gold"], text, re.I) else ("abstain" if ABSTAIN.search(text) else "wrong")
            rows.append({**e, "answer": text.strip()[:160], "status": status})
        res["dated_" + mode] = {"rows": rows}
        for grp in ["anchor", "before Sep 2024", "Sep 2024 to Jan 2025", "Feb 2025 to Jun 2025"]:
            rs = [r for r in rows if r["group"] == grp]
            print(f"dated {mode:8s} {grp:22s} correct {sum(r['status'] == 'correct' for r in rs)}/{len(rs)}  wrong {sum(r['status'] == 'wrong' for r in rs)}  abstain {sum(r['status'] == 'abstain' for r in rs)}", flush=True)

res["total_seconds"] = round(time.time() - t0)
json.dump(res, open(HERE / f"results_{slug}.json", "w"), indent=1, ensure_ascii=False)
print("done", slug, res["total_seconds"], "s")
