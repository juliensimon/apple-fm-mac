# 14. Memory-bandwidth contention

**In the article:** no, repository only. **Basis:** Measured. **Date:** 2026-10-24. **Machine:** MacBook Pro, Apple M3 Max (Mac15,9), 48 GB, macOS 27.0.1 (build 26A434).

## Hypothesis

Question: Does heavy CPU memory traffic slow the model?

No hypothesis was written before this test.

## Experiment

Run a CPU memory-bandwidth load (`membw.c`) at 200 GB/s while timing prefill and writing; run the same timing without the load.

From the repository root:

```
cc -O2 -o data/membw data/membw.c && python3 data/contention.py
python3 data/make_plot_data_contention.py
python3 scripts/check_numbers.py
```

Files:

- `data/contention.json`
- `data/plots/contention.csv`
- `data/membw.c`

## Results

- 200 GB/s of CPU memory traffic: writing 9% slower, a 2,000-token prefill 22% slower; the control without traffic did not change.

## Conclusion

Heavy CPU memory traffic slows Apple's model a little.

What it does not show:

- One load level, one Mac.
