# 02. Expert reads from flash

**In the article:** yes. **Basis:** Measured (timing, sizes); inferred (that the blocks are experts). **Date:** 2026-10-24 and 2026-10-25. **Machine:** MacBook Pro, Apple M3 Max (Mac15,9), 48 GB, macOS 27.0.1 (build 26A434).

## Hypothesis

H5 (written in `data/compare/inspect_ifp_cadence.sh` before the 2026-10-25 run): long-context median spacing 28 to 36 tokens holds, outside 24 to 40 fails. **Neither held nor failed** (37.6 tokens by mean speed, 40 by streamed position).

The rest of this item (sizes, first bursts, the 2026-10-24 cadence) answered the question with no hypothesis written first.

## Experiment

Trace the system calls of Apple's main inference process with `fs_usage` (root) during prompts on new subjects; group reads into bursts (gap under 0.12 s); stream the same answers again with timestamps to turn burst times into token positions.

From the repository root:

```
sudo bash data/inspect_ifp.sh   # 2026-10-24 trace
python3 data/make_plot_data_ifp.py
python3 data/essay_stream.py
sudo bash data/compare/inspect_ifp_cadence.sh   # 2026-10-25 trace
python3 data/compare/longctx_stream.py
python scripts/charts/make_charts_mac.py trace
python3 scripts/check_numbers.py
```

Files:

- `data/ifp_trace_2026-10-24/`
- `data/plots/ifp_reads.csv`
- `data/plots/ifp_phase_summary.csv`
- `data/plots/ifp_essay_clusters.csv`
- `data/essay_stream.json`
- `data/plots/ifp_cadence_reads.csv`
- `data/compare/ifp_cadence_out/`
- `data/compare/RESULTS_followups_2026-10-25.md`
- `plots/expert-reads.png`

## Results

- 2026-10-24, ten prompts: 1,384 reads of descriptor 3, every one 294,912 bytes, 389.2 MiB in total for 4,654 generated tokens (about 87,700 bytes per token). The file is `ifp_rasterized_weights.bin` (REPORT 21).
- First bursts of 152 to 228 blocks (43 to 64 MiB) in the first four prompts, 46 or fewer later, as the memory cache fills.
- Burst spacing, converted to tokens: code prompt 32 tokens (0.559 s at 58 tokens a second), essay 32 tokens (0.97 s at 33 tokens a second), geology 31 tokens (45 tokens a second, 2026-10-25). Three prompts, three speeds, one period of 31 to 32 tokens.
- Long-context prompt (3,872 tokens in, 2026-10-25): median spacing 40 tokens; many gaps are two to four times a 30-token step. Probable reason, read after the fact: a reselection that needs no new expert reads nothing.
- In the essay, the four large bursts land one or two periods before each new topic (REPORT 21.5).

## Conclusion

While it answers, Apple's model reads one 4.95 GB file in blocks of exactly 294,912 bytes, in bursts: a large burst after the prompt, then small bursts at a fixed spacing in tokens.

What it does not show:

- The trace records names, descriptors, offsets and sizes of system calls (`fs_usage`), never the contents of a read. The raw traces are not in this repository (they name files in Apple's protected asset folder); the reads are in `data/plots/`.
- That the blocks are expert weights is inferred: the byte count fits an expert of the published dimensions, and other shapes give the same count (768 x 768 at 4 bits).
- The stream arrives in blocks of about 10 tokens, so token positions are good to about 10 tokens.
- That 32 is a setting, rather than a measured regularity, is not shown.
