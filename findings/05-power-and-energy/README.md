# 05. Power and energy per problem

**In the article:** yes. **Basis:** Measured. **Date:** 2026-10-24 and 2026-10-25. **Machine:** MacBook Pro, Apple M3 Max (Mac15,9), 48 GB, macOS 27.0.1 (build 26A434).

## Hypothesis

H3, written in the docstring of `data/compare/energy_workload.py` before the 8-bit run: "Apple's model uses less energy per solved problem than each open build. Holds if its joules per solved problem are below all three." **Held** (35.7 J against 63.6 to 102.2). The 4-bit set then ran as the check the article's brief named before it ran (a 4-bit open build on the GPU that uses no more energy per solved problem would contradict the reading); it did not occur (40.7 J against 76.5 to 95.4).

## Experiment

Sample CPU, GPU and Neural Engine power with `powermetrics` every 500 ms (root) while each model answers the same 20 GSM8K problems through the same client; subtract the idle baseline; recompute from the raw samples with a second parser.

From the repository root:

```
sudo bash data/inspect_fm.sh   # power while Apple's model runs
sudo bash data/compare/run_energy.sh   # 8-bit set
sudo ENERGY_TAG=_4bit bash data/compare/run_energy.sh   # 4-bit set
python3 scripts/energy_recheck.py [_4bit]   # independent recomputation from the raw samples
python scripts/charts/make_charts_mac.py energy
```

Files:

- `data/plots/power_samples.csv`
- `data/root_run_2026-10-24/powermetrics.txt`
- `data/compare/energy_results.json`
- `data/compare/energy_results_4bit.json`
- `data/compare/powermetrics_energy.txt`
- `data/compare/powermetrics_energy_4bit.txt`
- `data/compare/phases.json`
- `data/compare/phases_4bit.json`
- `data/compare/*_4bit_slept.*`
- `data/compare/RESULTS_followups_2026-10-25.md`
- `plots/energy-mac.png`

## Results

- 2026-10-24: Neural Engine 4.2 W in prefill, 3.8 W in decode; GPU about 65 mW.
- 8-bit set (2026-10-25 00:48, idle baseline 185 mW): Apple 465 J above idle, 13 of 20 solved, 23.2 J per problem, 35.7 J per solved problem. Qwen3 4B 1,273 J (63.6 per solved), Gemma 3 4B 1,595 J (84.0), Gemma 4 E4B 1,942 J (102.2).
- 4-bit set, clean run (2026-10-25 07:50, idle baseline 461 mW): Apple 530 J, 26.5 J per problem, 40.7 per solved. Qwen3 4B 1,530 J (76.5), Gemma 4 E4B 1,680 J (88.4), Gemma 3 4B 1,716 J (95.4).
- At full GPU clock, halving the open builds' bit width did not cut their energy (Qwen3 4B: 1,273 J at 8 bits, 1,530 J at 4 bits).
- Apple's model on the same problems in three runs: 465, 440 and 530 J.
- The run with the Mac asleep (01:33, kept as `*_4bit_slept.*`, used for no comparison): after waking, the GPU ran at about 1,040 MHz instead of 1,380, and the same open builds used about half the energy. The clock macOS picks moves an open build's energy by a factor of about 1.8.

## Conclusion

Apple's model runs on the Neural Engine at about 4 W with the GPU idle, and uses less energy than every open build on the same 20 math problems, at 8 bits and at 4 bits.

What it does not show:

- `powermetrics` reports CPU, GPU and Neural Engine power only: no memory (DRAM), no SSD, no display.
- n = 20 problems, one run per set, all three runs on battery. Results on AC power were not measured.
- The comparison mixes the Neural Engine with a smaller active part of the model; this test cannot separate the two. Answer lengths were not recorded.
- Apple's model solved fewer problems (13 of 20), so per solved problem is the least favorable figure for it; totals and per problem are given first.
