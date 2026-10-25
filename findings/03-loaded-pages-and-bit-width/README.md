# 03. Loaded pages and the bit-width arithmetic

**In the article:** yes. **Basis:** Measured (page counts); inferred (bits per weight). **Date:** 2026-10-24. **Machine:** MacBook Pro, Apple M3 Max (Mac15,9), 48 GB, macOS 27.0.1 (build 26A434).

## Hypothesis

Question: How many weights can the loaded model pages hold, and at what bit width does one read block fit one expert?

No hypothesis was written before this test.

## Experiment

Count the model pages loaded in memory from the unified log; divide by bit widths; compare the read block size with Apple's published expert dimensions.

From the repository root:

```
python3 data/make_plot_data_card.py
python3 scripts/check_numbers.py
```

Files:

- `data/plots/parameter_budget.csv`
- `data/make_plot_data_card.py`

## Results

- 636 MiB of model pages (40,680 pages of 16 KiB). At 2 bits a weight that is at most 2.7 billion weights in memory; a prompt's new experts are 0.2 to 0.3 billion.
- 294,912 = 3 x 1,536 x 256 x 2 / 8: three matrices of 1,536 x 256 (the dimensions in Apple's paper) at 2 bits.

## Conclusion

The model pages loaded in memory are too few for 20 billion weights at more than about 2 bits, and the 294,912-byte block matches one expert at 2 bits.

What it does not show:

- The page counts were read from the unified log; that capture is not included.
- "About 2 bits" is inferred everywhere; Apple's 2025 report describes 2-bit quantization-aware training for its on-device model, and does not name this model.
