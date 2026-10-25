# 13. Dated events

**In the article:** no, repository only. **Basis:** Measured. **Date:** 2026-10-24. **Machine:** MacBook Pro, Apple M3 Max (Mac15,9), 48 GB, macOS 27.0.1 (build 26A434).

## Hypothesis

H2, written in the docstring of `data/compare/compare_models.py` before the open-model runs: "Core Advanced answers dated events like Gemma 3 4B does. Holds if its share of correct answers for events from September 2024 on is within 20 points of Gemma 3 4B's. Fails if it is 20 points or more above (a later data cutoff than Gemma 3's August 2024)." **Held**. Of the 14 events from September 2024 on, Apple's model got 4 and Gemma 3 4B 2 in the counts scored one by one (29% against 14%, 14 points); with the automatic scorer fixed beforehand (REPORT 29), 3 and 2.

## Experiment

Ask 28 questions on dated events in two modes (guess, and abstain allowed) to each model; score each answer one by one.

From the repository root:

```
python3 data/compare/dated_events_apple.py   # needs fm serve
python3 scripts/check_numbers.py
```

Files:

- `data/compare/dated_events.json`
- `data/compare/dated_handscored.json`
- `data/compare/results_*.json`

## Results

- Counts scored one by one, before September 2024: Apple 6, Gemma 3 6, Gemma 4 9, Qwen3 2; September 2024 to January 2025: 3, 2, 0, 2; February to June 2025: 1, 0, 0, 0.
- In abstain mode Apple's model said "I do not know" for all 7 events from February to June 2025 (and for the January 2025 event too).

## Conclusion

Asked about 28 dated events, Apple's model knows little after mid-2024 and says it does not know about 2025.

What it does not show:

- The 224 answers were scored one by one by the assistant model that ran the tests; a second model re-read them and agreed. REPORT 29 gives the automatic scorer's counts; the four answers on which they differ are listed in `dated_handscored.json`.
