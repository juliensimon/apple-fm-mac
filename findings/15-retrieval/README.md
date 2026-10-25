# 15. Finding one fact in a long prompt

**In the article:** no, repository only. **Basis:** Measured. **Date:** 2026-10-24. **Machine:** MacBook Pro, Apple M3 Max (Mac15,9), 48 GB, macOS 27.0.1 (build 26A434).

## Hypothesis

Question: Can the model find one fact in a long prompt?

No hypothesis was written before this test.

## Experiment

Plant one fact at several depths in prompts of up to 7,000 tokens and ask for it.

From the repository root:

```
python3 data/card_inputs/needle_test.py   # needs fm serve
python3 scripts/check_numbers.py
```

Files:

- `data/card_inputs/needle.json`
- `data/plots/needle_test.csv`

## Results

- 36 of 36 prompts of up to 7,000 tokens.

## Conclusion

Apple's model found one planted fact in every prompt tested, up to 7,000 tokens.

What it does not show:

- A single-fact test is easy; it says nothing about reasoning over a long prompt.
