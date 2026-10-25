# Follow-up runs, 2026-10-25 (run_followups.sh, 01:32 to 01:50 CEST, on battery)

MacBook Pro M3 Max (Mac15,9), 48 GB, macOS 27.0.1 (26A434).

## H5: expert reselection cadence, third trace (inspect_ifp_cadence.sh)

H5, written before the run: in the long-context prompt, the median spacing of read bursts after the first is 28 to 36
tokens (holds); outside 24 to 40 it fails.

**Verdict: neither held nor failed.** The median is 37.6 tokens when time is converted with the mean writing speed, and
40 tokens when each burst is placed in the answer by its own timestamp. Both values fall between 36 and 40.

Method: 423 reads of 294,912 bytes (B=0x48000) on descriptor 3 of the main provider, grouped into bursts with a 0.12 s
gap (same rule as docs/apple-fm/data/make_plot_data_ifp.py). Each answer was then streamed again with timestamps
(`longctx_stream.py`, and the same code for geology); both texts were identical to the traced runs. A burst time maps to
a character position, and `fm count-tokens` on the text up to that point gives a token position. The stream arrives in
blocks of about 10 tokens, so positions are good to about 10 tokens.

| Prompt | Prompt tokens | Answer tokens | Reads | Bursts | Gaps after the first, in tokens | Median |
|---|---|---|---|---|---|---|
| Geology (fresh subject) | about 30 | 454 | 285 | 15 | 30, 30, 30, 40, 30, 30, 40, 30, 40, 31, 30, 30, 39 | 30 |
| Long context | 3,872 | 910 | 138 | 17 | 19, 40, 31, 30, 40, 60, 40, 30, 90, 120, 71, 59, 40, 100, 60 | 40 |

- Geology: bursts every 0.695 s (standard deviation 0.053 s). From token 30 to token 430, 13 gaps: 30.8 tokens each on
  average, give or take about 1 from the 10-token resolution. With the 33 and 33 of 2026-10-24 (code at 58 tokens a
  second, essay at 33), that makes three prompts and three speeds with one period of 31 to 33 tokens.
- Long context: the gaps are not one period. Many are about twice, three times or four times a 30-token step (60, 90,
  120, 100). Read after the fact (not part of H5): a reselection that needs no new expert reads nothing, so it leaves no
  burst, and late in a long answer most experts are already in memory (138 reads against 285). A period scan does not
  settle it: at 10-token resolution, 32 fits better than chance (rms 4.9 against 9.2 expected) but 24 and 34 fit about
  as well.
- First burst of the long-context prompt: 71 reads at 1.92 s, while the prompt was still being read (first token at
  4.14 s in the stream). Observed once; cause not tested.
- Geology first burst: 96 reads. Burst sizes then fall from 34 to 3 to 17.

What this does not show: that the reads are expert weights (the byte count fits experts; other shapes give the same
count); that 32 is a setting rather than a measured regularity.

Files: data/plots/ifp_cadence_reads.csv (the reads; the raw fs_usage trace is not included), ifp_cadence_out/ (phases.txt,
out_*.txt, longctx_stream.json, geology_stream.json), longctx_stream.py.

## Energy, 4-bit set, clean run (ENERGY_TAG=_4bit run_energy.sh, 2026-10-25 07:50 to 07:59 CEST, on battery)

Run by Julien after the fix below. Samples continuous (no hole over 2 s, 998 samples, interval 0.511 to 0.527 s).
Independent recheck (scripts/energy_recheck.py _4bit) on the raw samples: every total within 0.4 J.

| Model | Solved | Window s | Mean mW | Above idle J | J per problem | J per solved | GPU clock (median) |
|---|---|---|---|---|---|---|---|
| Apple (Neural Engine) | 13 | 85.6 | 6,723 | 529.7 | 26.5 | 40.7 | GPU idle (338 MHz, 1.7% busy) |
| Qwen3 4B, 4-bit | 20 | 58.7 | 26,550 | 1,529.9 | 76.5 | 76.5 | 1,380 MHz |
| Gemma 4 E4B, 4-bit | 19 | 94.6 | 18,140 | 1,680.3 | 84.0 | 88.4 | 1,378 MHz |
| Gemma 3 4B, 4-bit | 18 | 71.2 | 24,560 | 1,716.4 | 85.8 | 95.4 | 1,380 MHz |

Idle baseline 460.7 mW (58 samples). Window edges moved by 2 s change totals by under 7%.

Power source: all three energy runs were on battery (pmset log; Julien confirmed for this one): charge 100% at 00:48,
93% at 01:33, 51% at 07:50. So the runs compare like with like on power source. No run was on AC power, and results on
AC power may differ (macOS can pick other clocks there); not measured.

Against the brief's falsifier ("a 4-bit open build on the GPU that uses no more energy per solved problem"): does not
trigger. Apple uses 53% of the best open build's energy per solved problem (40.7 J against 76.5 J) and 35% of its
total (530 J against 1,530 J).

What the 4-bit set adds to the 8-bit set of 00:48:
- Halving the open builds' bit width did not cut their energy at full GPU clock. Qwen3 4B: 1,273 J at 8 bits, 1,530 J
  at 4 bits (faster, 58.7 s against 84.0 s, but at 26.6 W against 15.3 W). Gemma 4 E4B: 1,942 J and 1,680 J. Gemma 3 4B:
  1,595 J and 1,716 J. So weight size alone does not explain Apple's lower energy; the Neural Engine and the smaller
  active part of the model remain, and this run cannot separate those two. Answer lengths were not recorded, so a
  change in answer length between the builds is not ruled out.
- Apple's model, three runs of the same 20 problems: 465 J (00:48), 440 J (01:33, with the sleep), 530 J (07:50).
  Spread about 20%. CPU power was higher in the last run (2,331 mW against 1,190 to 1,235); cause not established.
  Display kept on by caffeinate in the last run only.

## The run with the sleep (01:33), kept as *_4bit_slept.*: what it shows

The Mac went into idle sleep twice (pmset log: "Entering Sleep state due to 'Idle Sleep'" at 01:34:29 for 166 s,
during Apple's run, and at 01:39:30 for 284 s, during Gemma 3 4B; both woken by the trackpad). The power samples have
holes of 164 s and 282 s at those times. After the second wake, the GPU ran at a median 1,040 MHz instead of 1,380 for
Gemma 4 E4B and Qwen3 4B, and those two used about half the energy (918 J and 859 J against 1,680 J and 1,530 J in the
clean run), for 15% to 30% more time. So the energy of the same open build on the same problems moves by a factor of
about 1.8 with the clock macOS picks. Apple's model did not move that way (440 J in that run). Not used for any
comparison; kept because it shows how much the GPU clock matters.

Fix: run_energy.sh now holds `caffeinate -dims` for its own lifetime and prints the holes in the samples at the end
(tested: it flags the 01:33 run, passes the 00:48 run and passed the 07:50 run).
