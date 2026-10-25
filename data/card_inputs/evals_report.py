#!/usr/bin/env python3
"""Turn evals.json (written by evals.py) into CSV files and the numbers quoted in the model card.
MMLU groups follow the four groups of the MMLU authors' category list (STEM, humanities, social sciences, other).
Run: python3 data/card_inputs/evals_report.py   (reads evals.json here; writes evals_gsm8k_items.csv, evals_mmlu_items.csv and
evals_summary.csv into data/plots/, where the published copies are)"""
import csv, json, math, os, statistics as st

os.chdir(os.path.dirname(os.path.abspath(__file__)))   # the paths below are relative to this folder
P = os.path.join("..", "plots")

STEM = {"abstract_algebra", "astronomy", "college_biology", "college_chemistry", "college_computer_science", "college_mathematics", "college_physics",
        "computer_security", "conceptual_physics", "electrical_engineering", "elementary_mathematics", "high_school_biology", "high_school_chemistry",
        "high_school_computer_science", "high_school_mathematics", "high_school_physics", "high_school_statistics", "machine_learning"}
HUMANITIES = {"formal_logic", "high_school_european_history", "high_school_us_history", "high_school_world_history", "international_law", "jurisprudence",
              "logical_fallacies", "moral_disputes", "moral_scenarios", "philosophy", "prehistory", "professional_law", "world_religions"}
SOCIAL = {"econometrics", "high_school_geography", "high_school_government_and_politics", "high_school_macroeconomics", "high_school_microeconomics",
          "high_school_psychology", "human_sexuality", "professional_psychology", "public_relations", "security_studies", "sociology", "us_foreign_policy"}


def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return 100 * (c - h) / d, 100 * (c + h) / d


def group(subject):
    return "STEM" if subject in STEM else "Humanities" if subject in HUMANITIES else "Social sciences" if subject in SOCIAL else "Other"


d = json.load(open("evals.json")); g, m = d["gsm8k"], d["mmlu"]
for r in m: r["group"] = group(r["subject"])

with open(os.path.join(P, "evals_gsm8k_items.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["test_index", "gold", "predicted", "correct", "seconds", "output_tokens", "error"])
    for r in g: w.writerow([r["i"], r["gold"], r["pred"], int(r["right"]), r["seconds"], r["out_tokens"], r["error"] or ""])
with open(os.path.join(P, "evals_mmlu_items.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["test_index", "subject", "group", "gold", "predicted", "correct", "seconds", "error"])
    for r in m: w.writerow([r["i"], r["subject"], r["group"], r["gold"], r["pred"], int(r["right"]), r["seconds"], r["error"] or ""])

rows = []
def add(name, items, note):
    k = sum(r["right"] for r in items); n = len(items); lo, hi = wilson(k, n)
    rows.append([name, n, k, f"{100 * k / n:.1f}", f"{lo:.1f}", f"{hi:.1f}", sum(1 for r in items if r["error"]), note])
add("GSM8K (random test problems)", g, "zero-shot, step by step, final line 'Answer: N'; guardrail refusals count as wrong")
add("MMLU (random test questions)", m, "zero-shot, letter only; guardrail refusals count as wrong")
for name in ("STEM", "Humanities", "Social sciences", "Other"):
    add(f"MMLU, {name}", [r for r in m if r["group"] == name], "subset of the 200 questions")
answered = [r for r in m if not r["error"]]
add("MMLU, answered questions only", answered, "the 197 questions that did not trigger the guardrail")
with open(os.path.join(P, "evals_summary.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["benchmark", "n", "correct", "accuracy_pct", "ci95_low_pct", "ci95_high_pct", "guardrail_refusals", "note"]); w.writerows(rows)
for r in rows: print(r)

print("subjects covered:", len({r["subject"] for r in m}))
print("GSM8K seconds: median", st.median(r["seconds"] for r in g), "mean", round(st.mean(r["seconds"] for r in g), 2), "p90", sorted(r["seconds"] for r in g)[89], "max", max(r["seconds"] for r in g))
ot = [r["out_tokens"] for r in g if r["out_tokens"]]
print("GSM8K output tokens: median", st.median(ot), "mean", round(st.mean(ot), 1), "p90", sorted(ot)[int(.9 * len(ot))], "max", max(ot))
long = [r for r in g if (r["out_tokens"] or 0) > 1000]
print("GSM8K long outputs (>1000 tokens):", [(r["i"], r["out_tokens"], r["seconds"], r["right"]) for r in long])
wrong_noerr = [r for r in g if not r["right"] and not r["error"]]
print("GSM8K wrong without error:", len(wrong_noerr), "| no number found:", sum(1 for r in g if r["pred"] == ""))
print("MMLU seconds: median", st.median(r["seconds"] for r in m), "max", max(r["seconds"] for r in m))
