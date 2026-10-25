# 10. Speed and time to first token

**In the article:** no, repository only. **Basis:** Measured. **Date:** 2026-10-24. **Machine:** MacBook Pro, Apple M3 Max (Mac15,9), 48 GB, macOS 27.0.1 (build 26A434).

## Hypothesis

Question: How do time to first token and writing speed change with prompt length?

No hypothesis was written before this test.

## Experiment

Time 18 runs at prompt lengths from 20 to 6,900 tokens; fit straight-line, quadratic and cubic models of time to first token.

From the repository root:

```
python3 data/profile_ctx.py
python3 data/bench.py
python scripts/charts/make_charts_mac.py speed
python3 scripts/check_numbers.py
```

Files:

- `data/plots/ctx_profile.csv`
- `data/profile_ctx.json`
- `data/plots/prefill_early.csv`
- `data/bench-2026-10-24.json`
- `plots/speed-context.png`

## Results

- First token after 0.47 s at 20 prompt tokens, 1.60 s at 2,000 and 9.48 s at 6,900 (mean of two runs).
- Quadratic fit on the 18 runs: TTFT = 0.498 + 2.474e-4 n + 1.5555e-7 n^2 seconds, R^2 0.998 against 0.951 for a straight line (residual sum of squares 24.3 times smaller); a cubic term adds nothing.
- Prefill about 1,100 tokens a second at 1,000 to 3,000 tokens.
- Writing about 50 tokens a second on the math problems through `fm serve`; Gemma 3 63, Qwen3 65, Gemma 4 52 behind a local server called by the same client code (Gemma 3 73 in process).

## Conclusion

Time to the first token grows with the square of the prompt length, and writing speed halves by 5,000 tokens of prompt.

What it does not show:

- Speeds across servers are not a like-for-like comparison of the models; the same-client rerun narrows the gap, it does not close it.
