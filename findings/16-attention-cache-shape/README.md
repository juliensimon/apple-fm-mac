# 16. The attention cache shape

**In the article:** no, repository only. **Basis:** Measured (sizes); inferred (shape). **Date:** 2026-10-24. **Machine:** MacBook Pro, Apple M3 Max (Mac15,9), 48 GB, macOS 27.0.1 (build 26A434).

## Hypothesis

Question: What shape does the attention cache have?

No hypothesis was written before this test.

## Experiment

Read the sizes of the memory surfaces at several context lengths (root) and factor them.

From the repository root:

```
sudo bash data/inspect_scale.sh
python data/make_plot_data_scale.py
```

Files:

- `data/plots/iosurface_exact_sizes.csv`
- `data/plots/kv_pair_by_bucket.csv`
- `data/plots/kv_factorizations.csv`
- `data/plots/scale_run.csv`
- `data/scale_run_2026-10-24/scale_summary.tsv`

## Results

- One K or V tensor takes 35,840 bytes a token (293,601,280 = 8,192 x 35,840), which does not divide into twelve KV heads.

## Conclusion

The attention cache surfaces have sizes that do not fit the head count Apple published for its earlier model.

What it does not show:

- Sizes of memory surfaces only; the layout inside them is not read.
