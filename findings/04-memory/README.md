# 04. Memory at the same moments

**In the article:** yes. **Basis:** Measured. **Date:** 2026-10-24 and 2026-10-25. **Machine:** MacBook Pro, Apple M3 Max (Mac15,9), 48 GB, macOS 27.0.1 (build 26A434).

## Hypothesis

H4 (written in `data/compare/HYPOTHESIS_moe_footprint.md` before the run): the per-token mixture-of-experts build holds 12 GiB or more two seconds after the request; under 8 GiB fails. **Held** (15.0 GiB).

## Experiment

Read `footprint` for Apple's two processes (root) and for each open build served by `mlx_lm.server`, idle, during and two seconds after one 5,000-token request.

From the repository root:

```
sudo bash data/inspect_maps.sh   # Apple
bash data/compare/run_memory_protocol.sh   # open builds
python scripts/charts/make_charts_mac.py cost
python3 scripts/check_numbers.py
```

Files:

- `data/plots/footprint_categories.csv`
- `data/plots/iosurface_regions.csv`
- `data/compare/memory_protocol.json`
- `data/compare/memory_open_models.json`
- `data/compare/memory_footprint.json`
- `data/compare/HYPOTHESIS_moe_footprint.md`
- `data/compare/run_moe_footprint.log`
- `plots/cost-mac.png`

## Results

- Apple after the request: main process 1,361 MiB (293 MiB footprint plus 1,068 MiB owned by the neural engine driver), second process (safety models) 675 MiB, 2,036 MiB in all. Idle 2,848 MiB and during the request 3,437 MiB for both processes. So between 2.0 and 3.4 GiB at every moment measured.
- Open builds by the same tool at the same moments (one 5,000-token request): after, 3.4 to 4.6 GiB at 4 bits and 5.6 to 8.1 GiB at 8 bits.
- Gemma 4 26B A4B at 4 bits (25.2 billion parameters, 3.8 billion active per token), 2026-10-25: idle 14.0 GiB, during and peak 16.0, two seconds after 15.0, ten seconds after 15.0.
- The storage panel of `plots/cost-mac.png` (download sizes) lives here; its figures come from the sources cited in the article.

## Conclusion

Two seconds after a long request, Apple's two processes hold 2.0 GiB; the dense open builds hold 3.4 to 8.1 GiB, and a mixture-of-experts open build of a similar class holds about 15 GiB.

What it does not show:

- `footprint` prints whole gigabytes above about 10 GiB, so the mixture-of-experts figures are good to about 1 GiB.
- Apple's memory after minutes of rest was not measured; the root script reads to two seconds.
- MLX does not use Gemma's per-layer-embedding memory savings, so the Gemma figures are not Google's design at work.
- One Mac with 48 GB; a Mac with 16 GB or less may page differently.
