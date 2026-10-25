# 09. Same questions, same Mac

**In the article:** yes. **Basis:** Measured. **Date:** 2026-10-24. **Machine:** MacBook Pro, Apple M3 Max (Mac15,9), 48 GB, macOS 27.0.1 (build 26A434).

## Hypothesis

H1, written in the docstring of `data/compare/compare_models.py` before the open-model runs: "Gemma 3 4B lands within 10 points of Core Advanced on the same 100 GSM8K problems and 200 MMLU questions. Holds if both gaps are under 10 points. Fails if either gap is 10 points or more." **Failed**: the math gap is 11 points (89 against 78) and the knowledge gap 8 points (59.0% against 67.0%, in Apple's favor).

## Experiment

Ask 100 GSM8K and 200 MMLU questions, seeded draw, greedy decoding, to Apple's model through `fm serve` and to three 8-bit open builds; rerun the open builds behind a local server with the same client; compare paired answers with an exact McNemar test.

From the repository root:

```
python3 data/card_inputs/evals.py   # needs fm serve
zsh data/compare/run_all.sh
bash data/compare/run_server_checks.sh
python3 data/compare/paired.py
python data/compare/mmlu_uncapped.py
python3 scripts/check_numbers.py
```

Files:

- `data/card_inputs/evals.json`
- `data/compare/results_*.json`
- `data/compare/server_rerun_*.json`
- `data/compare/summary.json`
- `data/compare/mmlu_uncapped.json`
- `data/compare/recheck_gsm.json`
- `data/plots/same_questions.csv`
- `plots/same-questions.png`

## Results

- Math: Apple 78 of 100; Gemma 3 4B 89, Gemma 4 E4B 94, Qwen3 4B 93 (8-bit builds).
- Knowledge: Apple 134 of 200 (67.0%); Gemma 3 118 (59.0%), Gemma 4 139 (69.5%), Qwen3 144 (72.0%). Only the gap to Gemma 3 is large enough to see (exact McNemar p = 0.023 uncorrected, 0.068 after Holm).
- The open builds behind a local server, called by the same client code as Apple's model: no count moved by more than 1.
- Read from the final answer, eight MMLU replies without a letter change Qwen3 to 150 (75.0%) and Gemma 4 to 140.

## Conclusion

On 100 GSM8K math problems Apple's model solves fewer than the three open builds; on 200 MMLU questions it sits in the middle.

What it does not show:

- 8-bit open builds, greedy decoding, one run each, thinking turned off for Qwen3.
- Two open-model math replies reached the 1,000-token cap (Gemma 3 item 1140, Qwen3 item 1097); Apple's refusals count as wrong.
