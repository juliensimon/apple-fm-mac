# 06. The safety models' process

**In the article:** yes. **Basis:** Measured (memory, refusals); Apple says (the guardrails). **Date:** 2026-10-24. **Machine:** MacBook Pro, Apple M3 Max (Mac15,9), 48 GB, macOS 27.0.1 (build 26A434).

## Hypothesis

Question: What do the guardrails cost in memory, and how often do they refuse ordinary test questions?

No hypothesis was written before this test.

## Experiment

Read the second process's memory with the main one (item 04); count refusals over the 300 test questions (item 09).

From the repository root:

```
sudo bash data/inspect_maps.sh
python3 data/card_inputs/evals.py   # needs fm serve
python3 scripts/check_numbers.py
```

Files:

- `data/plots/footprint_categories.csv`
- `data/card_inputs/evals.json`
- `data/plots/evals_summary.csv`
- `data/compare/phases.json`

## Results

- Second process, two seconds after a long request: 140 MiB footprint plus 535 MiB outside it, 675 MiB.
- Refusals: 4 of 300 (1 math, GSM8K item 176; 3 knowledge). Through `fm serve` a refusal returns HTTP 500 with "The model's safety guardrails were triggered." The math refusal repeated in every energy run.

## Conclusion

Apple's guardrails run in a second process that holds about 0.7 GiB, and they refused 4 of 300 test questions.

What it does not show:

- Which models run in the second process is not shown; the label "safety models" follows from what Apple's pages describe.
