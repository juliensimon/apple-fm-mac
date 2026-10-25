# Manifest: where each number in the article comes from

The findings, numbered in the article's order, are in [`findings/INDEX.md`](findings/INDEX.md); the article's notes cite them by number.
The tables below map each number to its file. They are rebuilt for each version of the article.

Each row maps a number or figure of the article, by section, to the data file that holds it, the script that produced the data,
and the command that runs it. Every measurement was taken on one MacBook Pro (Apple M3 Max, 48 GB, macOS 27.0.1, build 26A434) on
2026-10-24. "check" means `python3 scripts/check_numbers.py`, which recomputes the number from the data file and prints it.
Commands are given from the repository root; scripts that need packages give their full `uv run` line in their first lines,
and the README lists them. "fm serve" means the script needs `fm serve --host 127.0.0.1 --port 18976` running
(18977 for the GSM8K recheck). "root" means `sudo`.

Numbers that come from Apple's pages, other publications or Hugging Face file listings (storage, download sizes, Apple's own
evaluations, vendor benchmark figures) are cited in the article's notes and are not data in this repository.

## Introduction

| Number or figure | Data file | Script | Command |
|---|---|---|---|
| 78 of 100 math problems; open models 89 to 94 | `data/card_inputs/evals.json`; `data/compare/results_*.json` | `data/card_inputs/evals.py` (fm serve); `data/compare/compare_models.py` | `python3 data/card_inputs/evals.py`; `zsh data/compare/run_all.sh`; check |
| In the middle of the pack on knowledge: 67.0% against 59.0%, 69.5% and 72.0%; only the gap to Gemma 3 is large enough to see (p = 0.023, uncorrected; adjusted 0.068 by Holm's method) | same | same | check |
| Two seconds after a request: 1.3 GiB (2.0 GiB with the safety models); open builds 3.4 to 8.1 GiB | `data/plots/footprint_categories.csv`; `data/compare/memory_protocol.json` | `data/inspect_maps.sh` (root); `data/compare/memory_protocol.py` | `sudo bash data/inspect_maps.sh`; `bash data/compare/run_memory_protocol.sh`; check |
| Neural Engine at about 4 W, GPU idle | `data/plots/power_samples.csv`, `data/root_run_2026-10-24/powermetrics.txt` | `data/inspect_fm.sh` (root) | `sudo bash data/inspect_fm.sh`; check |
| Apple's counter returned Gemma 3's count on all 429 strings | `data/tokenizer_test/counts_all_429.csv`; `data/card_inputs/apple_counts.json`, `fingerprint.json` | `data/card_inputs/apple_counts.py`, `fingerprint.py` (need the private corpus); `scripts/tokenizer_test.py` | check; `python scripts/tokenizer_test.py data/tokenizer_test/strings_public.csv` |

## What does a Mac get?

| Number or figure | Data file | Script | Command |
|---|---|---|---|
| The public API reports the larger model (Core Advanced), 8,192-token window, vision, guided generation and tool calling, no reasoning | REPORT 7.1 (program output, not saved as a file) | `data/public_api_query.swift` | `swiftc -O -parse-as-library data/public_api_query.swift -o runs/public_api_query && runs/public_api_query` |
| The window: a prompt of 8,102 tokens worked, 8,158 failed | `data/plots/context_limit_probe.csv` (typed from command output, REPORT 4.2) | `fm respond` by hand | check |
| `fm serve` streams by default, ignores `max_tokens`, rejects `stop` and `n`, takes `json_schema`, returns tool arguments as text | REPORT 7.2 (printed output) | `data/api2.py` (fm serve) | `python3 data/api2.py` |
| `fm serve` ignores `max_tokens` (73 tokens with and without it) and honors `max_completion_tokens`, loosely (10 tokens for a limit of 5, 20 for 20, finish reason "stop" both times) | `data/compare/probe_max_tokens.jsonl` | `data/compare/probe_max_tokens.py` (starts `fm serve` itself) | `python3 data/compare/probe_max_tokens.py` |

## What does it cost a Mac?

| Number or figure | Data file | Script | Command |
|---|---|---|---|
| Apple after the request: 293 MiB footprint plus 1,068 MiB neural-owned, 1,361 MiB, about 1.3 GiB; with the second process (140 plus 535 MiB) 2,036 MiB, about 2.0 GiB; idle 2,848 MiB and during 3,437 MiB for both processes | `data/plots/footprint_categories.csv` (snapshots idle, during and after; pids 9704 and 9700), `data/plots/iosurface_regions.csv` | `data/inspect_maps.sh` (root) | `sudo bash data/inspect_maps.sh`; check |
| Open builds by the same tool at the same moments (idle, during and two seconds after one 5,000-token request): after 3.4 to 4.6 GiB at 4 bits and 5.6 to 8.1 GiB at 8 bits; idle 2.6 to 8.0; largest reading during 4.4 to 9.4 | `data/compare/memory_protocol.json` (earlier readings, ten seconds after a short reply: `data/compare/memory_footprint.json`) | `data/compare/memory_protocol.py` | `bash data/compare/run_memory_protocol.sh`; check |
| MLX's own counters after loading: 4.50, 7.39 and 3.98 GiB | `data/compare/memory_open_models.json` | `data/compare/memory_open_models.py` | `python data/compare/memory_open_models.py`; check |
| Figure: storage and memory (`plots/cost-mac.png`) | `data/compare/memory_protocol.json`, `data/plots/footprint_categories.csv`; storage figures from the sources in the article | `scripts/charts/make_charts_mac.py` | `python scripts/charts/make_charts_mac.py cost` |
| A 4.95 GB file read in blocks of exactly 294,912 bytes | `data/plots/ifp_reads.csv`, `data/plots/parameter_budget.csv` | `data/inspect_ifp.sh` (root), then `data/make_plot_data_ifp.py` | `sudo bash data/inspect_ifp.sh`; check |
| First bursts of 152 to 228 blocks (43 to 64 MiB) in the first four prompts; later first bursts of 46 or fewer; small bursts about every 32 tokens | `data/plots/ifp_reads.csv`, `ifp_phase_summary.csv`, `ifp_essay_clusters.csv`; `data/essay_stream.json` | same; `data/essay_stream.py` | check (the bursts; the 32-token cadence is the burst spacing times the decode speed, REPORT 21.4) |
| 389.2 MiB over 4,654 generated tokens, about 87,700 bytes per token | `data/plots/ifp_reads.csv`, `ifp_phase_summary.csv` | same | check |
| Figure: expert reads over time (`plots/expert-reads.png`) | `data/plots/ifp_reads.csv` | `scripts/charts/make_charts_mac.py` | `python scripts/charts/make_charts_mac.py trace` |
| 636 MiB of model pages (40,680 pages of 16 KiB), at most 2.7 billion weights at 2 bits; a prompt's new experts 0.2 to 0.3 billion | `data/plots/parameter_budget.csv` | `data/make_plot_data_card.py` (page counts read from the unified log, whose capture is not included) | `python3 data/make_plot_data_card.py`; check |
| 294,912 = 3 x 1,536 x 256 x 2 bits / 8 (the paper's dimensions) | arithmetic | | check |
| One K or V tensor takes 35,840 bytes a token (293,601,280 = 8,192 x 35,840), which does not fit twelve KV heads | `data/plots/iosurface_exact_sizes.csv`, `kv_pair_by_bucket.csv`, `kv_factorizations.csv`, `scale_run.csv`; `data/scale_run_2026-10-24/scale_summary.tsv` | `data/inspect_scale.sh` (root), `data/make_plot_data_scale.py` | `sudo bash data/inspect_scale.sh`; `python data/make_plot_data_scale.py` |
| Neural Engine 4.2 W in prefill, 3.8 W in decode; GPU about 65 mW | `data/plots/power_samples.csv` | `data/inspect_fm.sh` (root) | check |
| 200 GB/s of CPU memory traffic: writing 9% slower, 2,000-token prefill 22% slower; no-traffic control unchanged | `data/plots/contention.csv`, `data/contention.json` | `data/contention.py`, `data/membw.c`, `data/make_plot_data_contention.py` | `cc -O2 -o data/membw data/membw.c && python3 data/contention.py`; check |
| About 1,100 tokens a second of prefill at 1,000 to 3,000 tokens | `data/plots/prefill_early.csv`, `data/bench-2026-10-24.json` | `data/bench.py` | `python3 data/bench.py`; check |
| First word after 0.5 s at 20 prompt tokens, 1.6 s at 2,000 and 9.5 s at 6,900 (mean of two runs: 0.47, 1.60, 9.48) | `data/plots/ctx_profile.csv` | `data/profile_ctx.py` | `python3 data/profile_ctx.py`; check |
| Writing about 50 tokens a second on the math problems, against 63 for Gemma 3 behind a local server called by the same client code (73 in process); Qwen3 65 and Gemma 4 52 behind the server | `data/card_inputs/evals.json`, `data/compare/server_rerun_*.json`, `data/compare/results_*.json` | as for the same questions | check |
| No prefix cache: the same 2,024-token prompt took 1.41 s on every repeat after the first (2.01 s) | `data/plots/api_cache_tests.csv` (typed from printed output) | `data/api.py` (fm serve) | `python3 data/api.py` |
| Figure: speed against prompt length (`plots/speed-context.png`) | `data/plots/ctx_profile.csv` (from `data/profile_ctx.json`) | `data/profile_ctx.py`; `scripts/charts/make_charts_mac.py` | `python3 data/profile_ctx.py`; `python scripts/charts/make_charts_mac.py speed` |

## How good is Core Advanced next to the models you would run?

| Number or figure | Data file | Script | Command |
|---|---|---|---|
| Figure: same questions, same Mac (`plots/same-questions.png`): 78, 89, 94, 93 of 100; 134, 118, 139, 144 of 200; intervals; 13 to 2, 18 to 2, 17 to 2; 14 to 30, 23 to 18, 25 to 15; exact p | `data/compare/summary.json`, `data/plots/same_questions.csv`, `data/tables.json`; from `data/card_inputs/evals.json` and `data/compare/results_*.json` | `data/compare/paired.py`; `scripts/charts/make_table_spec.py`, `scripts/charts/table.py` | `python3 data/compare/paired.py`; check; `python3 scripts/charts/make_table_spec.py` |
| My copy of Gemma 3 scored 89 and 59.0% | `data/compare/results_gemma3-4b-8bit.json`, `data/compare/log_gemma3-4b-8bit.txt` | `data/compare/compare_models.py` | `zsh data/compare/run_all.sh` |
| The three open builds behind a local server, called by the same client code as Apple's model: no count moved by more than 1 (Gemma 3 89 and 118, Gemma 4 93 and 140, Qwen3 93 and 144) | `data/compare/server_rerun_*.json` | `data/compare/server_rerun.py` | `bash data/compare/run_server_checks.sh`; check |
| Hypotheses written before the open-model runs (H1 failed, H2 held) | the docstring of `data/compare/compare_models.py` | | |
| Two open-model math replies reached the 1,000-token cap (Gemma 3 item 1140, Qwen3 item 1097) | `data/compare/results_*.json` | same | check |
| Apple's three answers that parsed as 0 were asked again; each still ends "Answer: 0" | `data/compare/recheck_gsm.json` | `data/compare/recheck_gsm.py` (fm serve on 18977) | `python data/compare/recheck_gsm.py` |
| Eight MMLU replies had no letter (Qwen3 6, Gemma 4 2); read from the final answer, Qwen3 150 (75.0%, 68.6 to 80.5; 28 to 12, p = 0.017) and Gemma 4 140 (70.0%; 24 to 18, p = 0.44) | `data/compare/mmlu_uncapped.json`, `data/compare/mmlu_revised.json` | `data/compare/mmlu_uncapped.py` | `python data/compare/mmlu_uncapped.py`; check |
| Refused 4 of 300 questions (1 math, item 176; 3 knowledge) | `data/card_inputs/evals.json`, `data/plots/evals_summary.csv` | `data/card_inputs/evals.py`, `evals_report.py` | check |
| Dated events: 28 questions in two modes; counts scored one by one (before September 2024: Apple 6, Gemma 3 6, Gemma 4 9, Qwen3 2; September 2024 to January 2025: 3, 2, 0, 2; February to June 2025: 1, 0, 0, 0); "I do not know" for all 7 events of 2025 | `data/compare/dated_events.json`, `data/compare/dated_handscored.json`, the `dated_*` sections of `data/compare/results_*.json` | `data/compare/dated_events_apple.py` (fm serve), `data/compare/compare_models.py` | `python3 data/compare/dated_events_apple.py`; check |
| One fact found in 36 of 36 prompts of up to 7,000 tokens | `data/card_inputs/needle.json`, `data/plots/needle_test.csv` | `data/card_inputs/needle_test.py` (fm serve) | `python3 data/card_inputs/needle_test.py`; check |
| If two models disagree on 20 questions, the winner needs 15 (p = 0.041 at 15 to 5, 0.115 at 14 to 6) | arithmetic | | check |

## Whose model is it?

| Number or figure | Data file | Script | Command |
|---|---|---|---|
| Figure: six descriptions of Google's role (`plots/six-sentences.png`) | `data/tables.json` (the quotations; sources in the article) | `scripts/charts/table.py` | `python scripts/charts/table.py data/tables.json plots/` |
| Gemma 3's tokenizer returned Apple's count on all 429 strings; the eight from other labs matched 20.7% to 44.5%; Gemma 2 75.5% | `data/tokenizer_test/counts_all_429.csv`; `data/tokenizer_fingerprint.csv` (= `data/plots/tokenizer_fingerprint.csv`); `data/card_inputs/fingerprint.json` | `data/card_inputs/fingerprint.py` (needs the private corpus); `scripts/tokenizer_test.py` | check |
| Figure: tokenizer exact matches (`plots/tokenizer-match.png`), Gemma 3n 100%, Gemma 4 99.1% | `data/tokenizer_fingerprint.csv`, `data/fingerprint_google.json` | `data/card_inputs/fingerprint_google.py`; `scripts/charts/make_charts.py` | `python scripts/charts/make_charts.py` |
| Google's endpoint returned Apple's count on all 257 strings sent, under four model names | `data/gemini_counttokens.json` | `data/gemini_counttokens.py` (needs `GEMINI_API_KEY`) | `python3 data/gemini_counttokens.py`; check |
| Gemma 4 misses four strings with `<h1>` or `<h2>`: 8, 8, 7, 8 tokens for Apple and Google's counter against 14, 14, 13, 14 | `data/card_inputs/fingerprint_google_diff.json`, `data/tokenizer_test/strings_public.csv` (ids 217, 224, 245, 257) | `data/card_inputs/fingerprint_google_diff.py` | check |
| Chat markers count as single tokens; 775 of the 6,242 placeholder slots no longer do | `data/plots/tokenizer_special_tokens.csv`, `data/plots/tokenizer_unused_slots.csv`, `data/card_inputs/unused_scan_full.json`, `apple_special.json` | `data/card_inputs/special_tokens_compare.py`, `scan_unused.py`, `data/make_plot_data_card.py` | `python3 data/card_inputs/scan_unused.py`; check |
| One user message costs 55 tokens in `fm serve`; Gemma 3's template explains 9 | `data/plots/chat_template_tokens.csv`, `data/card_inputs/template_probe.json` | `data/card_inputs/template_probe.py` (fm serve), `gemma_template_check.py` | `python3 data/card_inputs/template_probe.py`; check |
| A 192 MiB surface is 262,144 x 768 bytes | `data/plots/iosurface_exact_sizes.csv` | `data/inspect_maps.sh` (root) | check |

## What would change my mind

| Number or figure | Data file | Script | Command |
|---|---|---|---|
| The lightest open build I measured holds 3.4 GiB two seconds after a long request (Gemma 3 4B at 4 bits), against 2.0 GiB for Apple's two processes | `data/compare/memory_protocol.json`, `data/plots/footprint_categories.csv` | `data/compare/memory_protocol.py` | check |

## Notes on the data

- REPORT section 29 gives the dated-event counts of the automatic scorer, fixed beforehand. The article uses the counts scored one by one
  in `data/compare/dated_handscored.json`; the four answers on which they differ are listed in that file.
- `data/tokenizer_fingerprint.csv` and `data/plots/tokenizer_fingerprint.csv` are the same file, kept at both paths because the
  article cites the first and REPORT.md the second.
- `data/ane_bw.py` is the 1x1-convolution version of the Core ML benchmark, the one that produced `ane_bw_fp16.json` and
  `ane_bw_formats.json` (REPORT 20.1: the rank-2 `linear` layout never reached the Neural Engine).
- `data/gemini_counttokens.py` reads the 257 strings from `data/tokenizer_test/strings_public.csv`; the run of 2026-10-24
  selected the same 257 strings, in the same order, from the full corpus.
- `data/card_inputs/build_corpus.py` is redacted: the two private sampling steps and two strings with the author's name are
  removed, so it no longer rebuilds the corpus.
- `data/card_inputs/evals.py` downloads the two test files from the Hugging Face Hub and checks their SHA-256; the run of
  2026-10-24 read local copies of the same files. The seeded draw gives the same 100 and 200 items (checked).
- Scripts are as run, except: paths made relative to the script, run lines and docstrings updated, internal notes removed,
  `paired.py` printing p to four significant digits, and the changes listed above.
- Changed for publication on 2026-10-25: the model's name in script docstrings, the `repo` label of `data/compare/results_apple.json`
  and the label row of `data/plots/same_questions.csv` read "Core Advanced" (the hypotheses' wording is otherwise as written before
  the runs); the home folder in `data/compare/run_moe_footprint.log` is shown as `~`; the raw `fs_usage` trace of 2026-10-25 is
  replaced by its reads in `data/plots/ifp_cadence_reads.csv`.
- Pending when this repository was assembled: none. The six memory builds and the three local-server reruns finished on 2026-10-24.
