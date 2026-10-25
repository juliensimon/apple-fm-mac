#!/usr/bin/env python3
"""Recompute the article's headline numbers from the data files in this repository, and say where each one comes from.
Pure analysis: it reads data/ and calls nothing (no fm, no model, no network). Standard library only.
Run: python3 scripts/check_numbers.py            (from the repository root or from scripts/)
"""
import csv
import json
import math
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "data"
OPEN = [("gemma3-4b-8bit", "Gemma 3 4B"), ("gemma4-e4b-8bit", "Gemma 4 E4B"), ("qwen3-4b-8bit", "Qwen3 4B Instruct 2507")]


def load(p):
    return json.load(open(D / p))


def rows(p):
    return list(csv.DictReader(open(D / p, newline="")))


def wilson(k, n, z=1.959963984540054):
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return 100 * (c - h) / d, 100 * (c + h) / d


def mcnemar_exact(b, c):
    """Exact two-sided McNemar test on the discordant pairs: twice the binomial tail at p = 1/2, capped at 1."""
    n, k = b + c, min(b, c)
    return min(Fraction(1), 2 * sum(Fraction(math.comb(n, i), 2 ** n) for i in range(k + 1)))


def p_text(p):
    return f"{float(p):.4f}" if p >= Fraction(1, 1000) else f"{float(p):.5f}"


def head(t):
    print(f"\n== {t}")


# ---------------------------------------------------------------------------------------------------------------------------
head("Same questions: 100 GSM8K problems, 200 MMLU questions (data/card_inputs/evals.json, data/compare/results_*.json)")
apple = load("card_inputs/evals.json")
A = {b: {x["i"]: x["right"] for x in apple[b]} for b in ("gsm8k", "mmlu")}
res = {slug: load(f"compare/results_{slug}.json") for slug, _ in OPEN}
O = {slug: {b: {x["i"]: x["right"] for x in r[b]["rows"]} for b in ("gsm8k", "mmlu")} for slug, r in res.items()}
for b, n in (("gsm8k", 100), ("mmlu", 200)):
    k = sum(A[b].values()); lo, hi = wilson(k, n)
    print(f"Apple Core Advanced  {b:5s} {k:3d}/{n} = {100 * k / n:5.1f}%  95% Wilson {lo:4.1f} to {hi:4.1f}")
    for slug, name in OPEN:
        o = O[slug][b]; k = sum(o.values()); lo, hi = wilson(k, n)
        only_o = sum(1 for i in A[b] if o[i] and not A[b][i]); only_a = sum(1 for i in A[b] if A[b][i] and not o[i])
        print(f"{name:20s} {b:5s} {k:3d}/{n} = {100 * k / n:5.1f}%  95% Wilson {lo:4.1f} to {hi:4.1f}   only this model {only_o:2d} vs only Apple {only_a:2d}, exact McNemar p = {p_text(mcnemar_exact(only_o, only_a))}")
print(f"worked example, 20 questions on which two models disagree: 15 to 5 gives p = {p_text(mcnemar_exact(15, 5))}, 14 to 6 gives p = {p_text(mcnemar_exact(14, 6))}")
ref = {b: sum(1 for x in apple[b] if x["error"]) for b in ("gsm8k", "mmlu")}
print(f"Apple guardrail refusals, counted wrong: {ref['gsm8k']} GSM8K + {ref['mmlu']} MMLU = {sum(ref.values())} of 300")
for slug, name in OPEN:
    print(f"{name:20s} MMLU replies with no letter (counted wrong): {sum(1 for x in res[slug]['mmlu']['rows'] if not x['pred'])}")

head("MMLU read from the final answer after the eight cut replies were rerun uncapped (data/compare/mmlu_uncapped.json)")
unc = load("compare/mmlu_uncapped.json")
for slug, name, repo in (("qwen3-4b-8bit", "Qwen3 4B Instruct 2507", "mlx-community/Qwen3-4B-Instruct-2507-8bit"),
                         ("gemma4-e4b-8bit", "Gemma 4 E4B", "mlx-community/gemma-4-e4b-it-8bit")):
    o = dict(O[slug]["mmlu"])
    for key, v in unc.items():
        r, i = key.rsplit(":", 1)
        if r == repo:
            o[int(i)] = v["right"]
    k = sum(o.values()); lo, hi = wilson(k, 200)
    only_o = sum(1 for i in A["mmlu"] if o[i] and not A["mmlu"][i]); only_a = sum(1 for i in A["mmlu"] if A["mmlu"][i] and not o[i])
    print(f"{name:20s} {k}/200 = {k / 2:.1f}%  95% Wilson {lo:.1f} to {hi:.1f}   only this model {only_o} vs only Apple {only_a}, p = {p_text(mcnemar_exact(only_o, only_a))}")

head("Writing speed on the 100 math problems, all replies summed, prefill included (same files)")
tok = sum(x["out_tokens"] or 0 for x in apple["gsm8k"]); sec = sum(x["seconds"] for x in apple["gsm8k"])
print(f"Apple Core Advanced  {tok:6,d} tokens in {sec:6.1f} s = {tok / sec:5.1f} tokens/s  (fm serve; the refused request counts 0 tokens and its 0.25 s)")
for slug, name in OPEN:
    g = res[slug]["gsm8k"]["rows"]; tok = sum(x["out_tokens"] for x in g); sec = sum(x["seconds"] for x in g)
    capped = [x["i"] for x in g if x["out_tokens"] >= 1000]
    print(f"{name:20s} {tok:6,d} tokens in {sec:6.1f} s = {tok / sec:5.1f} tokens/s  (replies at the 1,000-token cap: {capped or 'none'})")

srv = sorted(D.glob("compare/server_rerun_*.json"))
if srv:
    head("Behind a local server (data/compare/server_rerun_*.json; threshold: every count within 3 of the in-process run)")
    for p in srv:
        r = json.load(open(p))
        dg, dm = r["gsm8k_correct"] - r["in_process_gsm8k_correct"], r["mmlu_correct"] - r["in_process_mmlu_correct"]
        print(f"{r['slug']:16s} GSM8K {r['gsm8k_correct']} (in process {r['in_process_gsm8k_correct']}), MMLU {r['mmlu_correct']} (in process {r['in_process_mmlu_correct']}), "
              f"items that changed {r['gsm8k_items_that_changed']} and {r['mmlu_items_that_changed']}: {'holds' if abs(dg) <= 3 and abs(dm) <= 3 else 'fails'}")
        tk = sum(x["out_tokens"] for x in r["gsm8k"] if x.get("out_tokens")); sc = sum(x["seconds"] for x in r["gsm8k"] if x.get("out_tokens"))
        print(f"{'':16s} writing speed over the 100 math problems, behind the server: {tk:,d} tokens in {sc:.1f} s = {tk / sc:.1f} tokens/s")

# ---------------------------------------------------------------------------------------------------------------------------
head("Dated events, scored one by one, guess mode (data/compare/dated_handscored.json)")
hs = load("compare/dated_handscored.json")["summary"]
names = {"apple": "Apple", "g3": "Gemma 3", "g4": "Gemma 4", "qw": "Qwen3"}
for grp in ("before Sep 2024", "Sep 2024 to Jan 2025", "Feb 2025 to Jun 2025"):
    print(f"{grp:22s} " + ", ".join(f"{names[m]} {hs['guess'][m][grp]['C']}" for m in names))
ab = hs["abstain"]["apple"]
print(f"Apple, abstain mode, 'I do not know': {ab['before Sep 2024']['A']} of 11 events before September 2024, {ab['Feb 2025 to Jun 2025']['A']} of 7 from February to June 2025")

# ---------------------------------------------------------------------------------------------------------------------------
head("Tokenizer: exact token counts against Apple's on 429 strings (data/tokenizer_test/counts_all_429.csv)")
tk = rows("tokenizer_test/counts_all_429.csv")
cols = [c for c in tk[0] if c not in ("id", "category", "characters", "text_in_strings_public", "apple_fm") and not c.startswith("google_")]
for c in sorted(cols, key=lambda c: -sum(r[c] == r["apple_fm"] for r in tk)):
    k = sum(r[c] == r["apple_fm"] for r in tk)
    print(f"{c:16s} {k:3d}/429 = {100 * k / 429:5.1f}%")
pub = [r for r in tk if r["text_in_strings_public"] == "yes"]
for c in [c for c in tk[0] if c.startswith("google_")]:
    print(f"{c:30s} equal to Apple on {sum(r[c] == r['apple_fm'] for r in pub)}/{len(pub)} strings sent")
stt = rows("plots/tokenizer_special_tokens.csv")
print(f"special-looking strings: Apple and Gemma 3 agree on {sum(r['agree'] == 'True' for r in stt)} of {len(stt)} (data/plots/tokenizer_special_tokens.csv)")
us = [r for r in rows("plots/tokenizer_unused_slots.csv")]
multi = [int(r["unused_slot_n"]) for r in us if int(r["apple_tokens"]) > 1]
print(f"reserved slots <unusedN>: {len(us)} counted, {len(us) - len(multi)} still one token, {len(multi)} not (from {min(multi)}; data/plots/tokenizer_unused_slots.csv)")
ctt = {r["case"]: r for r in rows("plots/chat_template_tokens.csv")}
print(f"fm serve framing: one user message {ctt['user hi']['framing_tokens']} tokens, with a system message {ctt['system + user']['framing_tokens']}, "
      f"each further assistant-and-user pair {int(ctt['user, assistant, user']['framing_tokens']) - int(ctt['user hi']['framing_tokens'])} (data/plots/chat_template_tokens.csv)")
sp = {r["id"]: r for r in rows("tokenizer_test/strings_public.csv")}
diff = [r for r in tk if r["gemma4_e4b"] != r["apple_fm"]]
print("Gemma 4 E4B differs on ids", [r["id"] for r in diff], "Apple", [r["apple_fm"] for r in diff], "Gemma 4", [r["gemma4_e4b"] for r in diff],
      "Google's counter", [sp[r["id"]]["google_gemma_4_31b_it"] for r in diff], "texts", [sp[r["id"]]["text"] for r in diff])

# ---------------------------------------------------------------------------------------------------------------------------
head("Memory held (data/plots/footprint_categories.csv for Apple, data/compare/memory_protocol.json for the open builds; footprint prints MB for MiB)")
fp = {(r["snapshot"], r["pid"], r["category"]): r for r in rows("plots/footprint_categories.csv")}
mb = lambda s: float(s.split()[0]) * {"B": 1 / 2**20, "KB": 1 / 1024, "MB": 1, "GB": 1024}[s.split()[1]]


def held(snapshot, pid):
    """The process's whole footprint (dirty total) and the Neural Engine memory macOS leaves out of it."""
    foot = sum(mb(fp[(snapshot, pid, "TOTAL")][c]) for c in ("dirty",))
    out = sum(mb(fp[(snapshot, pid, c)][col]) for c in ("Owned physical footprint (unmapped) (neural) (nofootprint)", "IOKit (neural) (nofootprint)") if (snapshot, pid, c) in fp for col in ("dirty", "clean", "reclaimable"))
    return foot, out


for snap in ("after", "idle", "during"):
    (fa, oa), (fb, ob) = held(snap, "9704"), held(snap, "9700")
    print(f"Apple, {snap:6s}: main process {fa:,.0f} + {oa:,.0f} outside the footprint = {fa + oa:,.0f} MiB; second process (safety models) {fb:,.0f} + {ob:,.0f} = {fb + ob:,.0f} MiB; "
          f"both {fa + oa + fb + ob:,.0f} MiB = {(fa + oa + fb + ob) / 1024:.2f} GiB   (main alone {(fa + oa) / 1024:.2f} GiB)")
mo = load("compare/memory_open_models.json")["models"]
print("MLX's own counters after loading the 8-bit builds: " + ", ".join(f"{k.split('/')[1]} {v['after_load_gib']:.2f}" for k, v in mo.items()) + " GiB  (data/compare/memory_open_models.json)")
mp = load("compare/memory_protocol.json")
print("Open builds at Apple's moments, GiB: idle / largest reading during the request / two seconds after (data/compare/memory_protocol.json)")
for r in sorted(mp, key=lambda r: r["footprint_mib_after_2s"]):
    print(f"  {r['label']:16s} {r['footprint_mib_idle'] / 1024:5.2f} / {r['footprint_mib_peak'] / 1024:5.2f} / {r['footprint_mib_after_2s'] / 1024:5.2f}   (prompt {r['prompt_tokens']} tokens, {r['readings']} readings during the request)")
for bits in ("4bit", "8bit"):
    v = [r["footprint_mib_after_2s"] / 1024 for r in mp if r["label"].endswith(bits)]
    print(f"  after, {bits[0]} bits: {min(v):.1f} to {max(v):.1f} GiB")
mf = load("compare/memory_footprint.json")
for bits in ("8bit", "4bit"):
    v = sorted((r["footprint_mib_ten_seconds_later"] / 1024, r["label"]) for r in mf if r["label"].endswith(bits))
    print(f"Earlier readings at {bits[0]} bits, ten seconds after a reply of at most 300 tokens: " + ", ".join(f"{l} {g:.1f}" for g, l in v) + " GiB  (data/compare/memory_footprint.json)")

# ---------------------------------------------------------------------------------------------------------------------------
head("Power during one prefill and one decode (data/plots/power_samples.csv, powermetrics at 250 ms)")
ps = rows("plots/power_samples.csv")
for ph in ("prefill_5k", "decode_400w"):
    s = [r for r in ps if r["phase"] == ph]
    print(f"{ph:12s} {len(s):3d} samples: ANE mean {sum(float(r['ane_mw']) for r in s) / len(s):6,.0f} mW, GPU mean {sum(float(r['gpu_mw']) for r in s) / len(s):3.0f} mW")
print(f"whole run   {len(ps):3d} samples: GPU mean {sum(float(r['gpu_mw']) for r in ps) / len(ps):.0f} mW")

# ---------------------------------------------------------------------------------------------------------------------------
head("Expert reads (data/plots/ifp_reads.csv: fs_usage on the weight file; data/plots/ifp_phase_summary.csv)")
ir = rows("plots/ifp_reads.csv")
sizes = {int(r["bytes"]) for r in ir}
total = sum(int(r["bytes"]) for r in ir)
print(f"{len(ir):,d} reads, sizes {sorted(sizes)} bytes, {total / 2**20:.1f} MiB in all")
by = defaultdict(list)
for r in ir:
    by[r["phase"]].append(float(r["seconds_into_phase"]))
first = {}
for ph, ts in by.items():
    ts.sort(); c = [ts[0]]
    for t in ts[1:]:
        if t - c[-1] < 0.12:
            c.append(t)
        else:
            break
    first[ph] = (len(c), c[0])
order = [r["phase"] for r in rows("plots/ifp_phase_summary.csv")]
print("first burst, reads (start in seconds): " + ", ".join(f"{ph} {first[ph][0]} ({first[ph][1]:.2f})" for ph in order))
toks = sum(int(r["output_tokens"]) for r in rows("plots/ifp_phase_summary.csv"))
print(f"bytes read per generated token: {total:,d} / {toks:,d} = {total / toks:,.0f}")
for ph in order[:4]:
    print(f"  {ph}: {first[ph][0]} reads = {first[ph][0] * 294912 / 2**20:.1f} MiB = {first[ph][0] * 294912 * 4 / 1e9:.2f} billion weights at 2 bits")
print(f"later prompts' first bursts: {max(first[ph][0] for ph in order[4:])} reads at most")

# ---------------------------------------------------------------------------------------------------------------------------
head("Sizes (data/plots/parameter_budget.csv, data/plots/iosurface_exact_sizes.csv)")
pb = {r["component"]: r for r in rows("plots/parameter_budget.csv")}
st = pb["routed-expert store (ifp_rasterized_weights.bin)"]; pg = pb["always-resident ANE model pages (log: 40,680 pages)"]
print(f"weight file {int(st['bytes']):,d} bytes; resident model pages {int(pg['bytes']):,d} bytes = {int(pg['bytes']) / 2**20:.1f} MiB = at most {int(pg['bytes']) * 4 / 1e9:.2f} billion weights at 2 bits")
kv = [int(r["bytes"]) for r in rows("plots/iosurface_exact_sizes.csv")]
print(f"largest IOSurface {max(kv):,d} bytes = 8,192 x {max(kv) // 8192:,d}" + (" (exact)" if max(kv) % 8192 == 0 else ""))
print(f"persistent 192 MiB surface present: {201326592 in kv}; 262,144 x 768 = {262144 * 768:,d}")
print(f"expert block: 3 x 1,536 x 256 x 2 bits / 8 = {3 * 1536 * 256 * 2 // 8:,d} bytes (the paper's dimensions; the measured block is {sorted(sizes)[0]:,d})")

# ---------------------------------------------------------------------------------------------------------------------------
head("Speed against context (data/plots/ctx_profile.csv, data/plots/prefill_early.csv, data/bench-2026-10-24.json)")
cp = rows("plots/ctx_profile.csv")
byn = defaultdict(list)
for r in cp:
    byn[int(r["prompt_tokens"])].append(r)
mean = lambda v: sum(v) / len(v)
for n in sorted(byn):
    rs = byn[n]
    print(f"prompt {n:5d} tokens: time to first token {mean([float(r['ttft_s']) for r in rs]):5.2f} s, writing {mean([float(r['decode_tok_s']) for r in rs]):5.1f} tokens/s"
          + ("" if rs[0]["output_is_counting_task"] == "1" else "  (different output, left out of decode fits)"))
pe = {int(r["prompt_tokens"]): float(r["wall_seconds"]) for r in rows("plots/prefill_early.csv")}
print(f"marginal prefill rate, 1,010 to 3,012 tokens: {(3012 - 1010) / (pe[3012] - pe[1010]):,.0f} tokens/s")
b = load("bench-2026-10-24.json")
print(f"prose: {b['decode_nostream']['out_tokens']} tokens in {b['decode_nostream']['seconds']:.2f} s, first streamed chunk at {b['decode_stream']['first_chunk_s']:.2f} s")

# ---------------------------------------------------------------------------------------------------------------------------
head("Other results")
nd = load("card_inputs/needle.json")
print(f"long-context retrieval: {sum(r['correct'] for r in nd)} of {len(nd)} correct, prompts of {min(r['prompt_tokens'] for r in nd):,d} to {max(r['prompt_tokens'] for r in nd):,d} tokens (data/card_inputs/needle.json)")
ct = {r["condition"]: r for r in rows("plots/contention.csv")}
c = ct["copy x12"]; s = ct["spin x12 (control)"]
print(f"memory contention: {c['hog_gb_per_s']} GB/s of CPU copy traffic -> writing {c['short_decode_change_pct']}%, 2,000-token prefill +{c['prefill_2k_change_pct']}%; "
      f"control with no memory traffic {s['short_decode_change_pct']}% and +{s['prefill_2k_change_pct']}% (data/plots/contention.csv)")
ac = [r for r in rows("plots/api_cache_tests.csv") if r["test"] == "same_prompt"]
print(f"no prefix cache in fm serve: the same {ac[0]['prompt_tokens']}-token prompt took " + ", ".join(f"{float(r['seconds']):.2f}" for r in ac)
      + f" s, cached_tokens {sorted({r['cached_tokens'] for r in ac})} (data/plots/api_cache_tests.csv)")
lim = rows("plots/context_limit_probe.csv")
print("context limit: " + ", ".join(f"{r['counted_prompt_tokens']} {r['result']}" for r in lim if int(r["counted_prompt_tokens"]) >= 8000) + " (data/plots/context_limit_probe.csv)")

# ---------------------------------------------------------------------------------------------------------------------------
head("Time to first token against prompt length: straight line, quadratic and cubic fits on the 18 runs (data/plots/ctx_profile.csv)")


def polyfit(xs, ys, deg):
    m = deg + 1
    a = [[sum(x ** (i + j) for x in xs) for j in range(m)] + [sum(y * x ** i for x, y in zip(xs, ys))] for i in range(m)]
    for c in range(m):
        p = max(range(c, m), key=lambda r: abs(a[r][c])); a[c], a[p] = a[p], a[c]
        for r in range(m):
            if r != c:
                f = a[r][c] / a[c][c]; a[r] = [u - f * v for u, v in zip(a[r], a[c])]
    return [a[i][m] / a[i][i] for i in range(m)]


xs = [float(r["prompt_tokens"]) for r in cp]; ys = [float(r["ttft_s"]) for r in cp]
sst = sum((y - mean(ys)) ** 2 for y in ys)
sse = {}
for deg in (1, 2, 3):
    co = polyfit(xs, ys, deg)
    sse[deg] = sum((y - sum(c * x ** i for i, c in enumerate(co))) ** 2 for x, y in zip(xs, ys))
    print(f"degree {deg}: coefficients {', '.join(f'{c:.4g}' for c in co)}; R^2 {1 - sse[deg] / sst:.3f}; rmse {math.sqrt(sse[deg] / len(xs)):.3f} s")
print(f"{len(xs)} runs; residual sum of squares, straight line over quadratic: {sse[1] / sse[2]:.1f} times")

# ---------------------------------------------------------------------------------------------------------------------------
head("Energy for the same 20 GSM8K problems, CPU + GPU + Neural Engine above idle (data/compare/energy_results*.json; raw samples: scripts/energy_recheck.py)")
for tag, label in (("", "8-bit set, 2026-10-25 00:48"), ("_4bit", "4-bit set, clean run, 2026-10-25 07:50")):
    er = load(f"compare/energy_results{tag}.json")
    print(f"{label}, idle baseline {er['idle_baseline_mw']:.0f} mW")
    for k, m in er["models"].items():
        print(f"  {k:16s} solved {m['solved']:2d}/{m['problems']}  {m['energy_above_idle_j']:7.1f} J  = {m['j_per_problem_above_idle']:5.1f} J per problem, "
              f"{m['j_per_solved_above_idle']:5.1f} J per solved  (mean ANE {m['mean_ane_mw']} mW, GPU {m['mean_gpu_mw']} mW, CPU {m['mean_cpu_mw']} mW)")
    a = er["models"]["apple"]; best = min((m for k, m in er["models"].items() if k != "apple"), key=lambda m: m["j_per_solved_above_idle"])
    print(f"  Apple per solved problem as a share of the best open build: {a['j_per_solved_above_idle'] / best['j_per_solved_above_idle']:.0%}; total: {a['energy_above_idle_j'] / best['energy_above_idle_j']:.0%}")
