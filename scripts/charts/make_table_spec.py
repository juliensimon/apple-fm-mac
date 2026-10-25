#!/usr/bin/env python3
"""Writes the 'same-questions' table spec into data/tables.json from data/compare/summary.json (GSM8K and MMLU) and, with
--final-answer, data/compare/mmlu_revised.json (MMLU, eight cut replies rerun). The published table uses the default rule.
Run: python3 scripts/charts/make_table_spec.py ["<title>"] [--final-answer]   then: python3 scripts/charts/table.py data/tables.json plots/"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
C = HERE.parents[1] / "data" / "compare"
S = json.load(open(C / "summary.json"))
FINAL = "--final-answer" in sys.argv
M = json.load(open(C / "mmlu_revised.json"))["models"] if FINAL else None
args = [a for a in sys.argv[1:] if not a.startswith("--")]
title = args[0] if args else "Same questions, same Mac: Apple's model is last on math and mid-pack on knowledge"


def pill(only_model, only_apple, p):
    if p < 0.05:
        return ("red", "Apple behind") if only_model > only_apple else ("green", "Apple ahead")
    return ("grey", "no clear gap")


def cell(text, sub=None, pill_=None):
    d = {"text": text, "mono": True}
    if sub:
        d["sub"] = sub
    if pill_:
        d["pill"], d["pill_text"] = pill_
    return d


def p_text(p):
    return "p < 0.001" if p < 0.001 else ("p = %.3f" % p if p < 0.01 else "p = %.2f" % p)


rows = []
a = S["apple"]
rows.append([{"text": "Apple Core Advanced", "sub": "Apple's figures: 20B stored, 1 to 4B at work"}, cell(str(a["g"][0]), "%d to %d" % tuple(a["g"][2])), cell(""),
             cell("%d (%.1f%%)" % (a["m"][0], a["m"][0] / 2), "%d to %d" % tuple(a["m"][2])), cell("")])
meta = {"gemma3-4b-8bit": ("Gemma 3 4B", "Google, 4B parameters"), "gemma4-e4b-8bit": ("Gemma 4 E4B", "Google, 4.5B effective"), "qwen3-4b-8bit": ("Qwen3 4B Instruct 2507", "Alibaba, 4B parameters")}
for slug, (name, sub) in meta.items():
    g = S[slug]; m = M[slug] if M else None
    gp = g["gp"]  # (only Apple, only model, p)
    if FINAL:
        k, ci, om, oa, pv = m["correct"], m["ci"], m["only_model"], m["only_apple"], m["p"]
    else:
        k, ci, om, oa, pv = g["m"][0], g["m"][2], g["mp"][1], g["mp"][0], g["mp"][2]
    rows.append([{"text": name, "sub": sub},
                 cell(str(g["g"][0]), "%d to %d" % tuple(g["g"][2])),
                 cell("%d vs %d" % (gp[1], gp[0]), p_text(gp[2]), pill(gp[1], gp[0], gp[2])),
                 cell("%d (%.1f%%)" % (k, k / 2), "%d to %d" % (round(ci[0]), round(ci[1]))),
                 cell("%d vs %d" % (om, oa), p_text(pv), pill(om, oa, pv))])
spec = {
    "slug": "same-questions", "title": title,
    "subtitle": "100 GSM8K problems and 200 MMLU questions, zero-shot, temperature 0",
    "columns": [{"head": "Model"}, {"head": "Math solved", "sub": "of 100, 95% interval"}, {"head": "Against Apple", "sub": "only this model vs only Apple"},
                {"head": "Knowledge right", "sub": "of 200, 95% interval"}, {"head": "Against Apple", "sub": "only this model vs only Apple"}],
    "rows": rows,
    "legend": "Pills: exact paired test (McNemar) on the same questions. Red or green mean a gap too large for chance at the 5% level; grey means no clear gap.",
    "source": "Author's measurement, MacBook Pro (M3 Max, macOS 27.0.1): Apple through fm serve, open models as 8-bit MLX builds. Data: data/compare/",
    "source_date": "2026-10-24", "day": "2026-10-26",
}
tp = C.parent / "tables.json"
specs = [s for s in json.load(open(tp)) if s.get("slug") != "same-questions"] + [spec]
json.dump(specs, open(tp, "w"), indent=2, ensure_ascii=False)
for r in rows:
    print([c["text"] if isinstance(c, dict) else c for c in r])
