# Plot-ready data

All series behind `../../REPORT.md`, as CSV. Most were built by a script that read raw files this repository does not keep
(process snapshots, region maps and `fs_usage` traces, which name files inside Apple's protected asset folder). The builders
that run from the files here are `data/make_plot_data_card.py`, `make_plot_data_contention.py` and `make_plot_data_scale.py`;
`make_plot_data_ifp.py` needs an expert-loading trace of your own (`data/inspect_ifp.sh`). Machine: Apple M3 Max, 48 GB, macOS 27.0.1 (26A434), 2026-10-24.
Times are single runs unless a `rep` column says otherwise. Bytes are exact; "MB" columns say so in their name.

| File | Rows | What it holds | Columns |
|---|---|---|---|
| `ctx_profile.csv` | 18 | TTFT and decode speed against prompt length, 2 reps (report 14) | `prompt_tokens, rep, ttft_s, decode_s, out_tokens, decode_tok_s, ms_per_token, total_s, output_is_counting_task` |
| `prefill_early.csv` | 6 | First prefill series, wall time per prompt length (report 4.1) | `prompt_tokens, wall_seconds` |
| `context_limit_probe.csv` | 9 | Where the 8,192-token window fails (report 4.2) | `counted_prompt_tokens, wall_seconds, result` |
| `decode_stream_chunks.csv` | 177 | Arrival time and size of every streamed chunk of a 309-token answer | `t_seconds, chunk_bytes` |
| `startup_tiny_prompt.csv` | 3 | Wall time of a one-word answer (process start included) | `run, wall_seconds` |
| `power_samples.csv` | 160 | `powermetrics` at 250 ms: ANE, GPU, CPU power and GPU clock (report 11.1) | `epoch_s, local_time, elapsed_ms, phase, ane_mw, gpu_mw, cpu_mw, combined_mw, gpu_freq_mhz, gpu_residency_pct` |
| `phase_markers.csv` | 12 | Epoch time of each workload phase boundary | `marker, epoch_s` |
| `gpu_cpu_samples.csv` | 282 | GPU utilization (ioreg) and provider CPU time, every 50 ms (report 6.2) | `t_seconds, phase, gpu_device_util_pct, gpu_renderer_util_pct, gpu_in_use_system_memory_bytes, provider_cpu_seconds_total, provider_rss_kb_total` |
| `memory_by_region_type.csv` | 255 | `vmmap` regions summed by type, per pid and snapshot (report 12.1) | `pid, snapshot, region_type, regions, virtual_bytes, resident_bytes, dirty_bytes` |
| `iosurface_regions.csv` | 262 | Every IOSurface region with its SurfaceID and tag (report 12.2) | `pid, snapshot, start, virtual_bytes, resident_bytes, dirty_bytes, prot, surface_id, tag` |
| `neural_and_gpu_regions.csv` | 50 | ANE-reserved, IOKit (neural) and GPU carveout ranges (report 12.3) | `pid, snapshot, region_type, start, end, virtual_bytes, resident_bytes, prot, share_mode` |
| `footprint_categories.csv` | 181 | `footprint` categories per pid and snapshot | `snapshot, pid, category, dirty, clean, reclaimable, regions` (values as printed, with units) |
| `fs_usage_op_counts.csv` | 23 | File-system call counts of the providers during the workload (report 11.4) | `operation, count` |
| `tokenizer_special_strings.csv` | 48 | Token count of reserved and special strings (report 15.1) | `string, tokens` |
| `tokenizer_general_strings.csv` | 9 | Digits, emoji, spaces, hex, URL | `label, characters, tokens` |
| `tokenizer_languages.csv` | 18 | The same sentence in 18 languages (report 16.1) | `language, characters, tokens, ratio_vs_english, chars_per_token, supports_locale_api` |
| `instruction_wrapper_overhead.csv` | 5 | The fixed 46-token wrapper around instructions (report 4.4) | `instruction_words, tokens_as_prompt, tokens_as_instructions` |
| `api_cache_tests.csv` | 10 | No prefix caching over HTTP (report 7.3) | `test, call, prompt_tokens, seconds, cached_tokens` |
| `image_latency.csv` | 6 | Latency with an image, 64 to 2048 px (report 4.6) | `image_px, run1_seconds, run2_seconds` |
| `scale_run.csv` | 20 | Peak IOSurface memory against prompt length, two passes (report 18.2) | `pass, reps, counted_prompt_tokens, effective_tokens_assumed_template_56, bucket, wall_seconds, peak_iosurface_resident_mib, model_fixed_plus_kv_pair_mib, error_mib, vmmap_samples` |
| `kv_pair_by_bucket.csv` | 5 | K and V tensor size for each context bucket (report 18.3) | `bucket_tokens, bytes_per_tensor, mib_per_tensor, mib_k_plus_v_pair, seen_in_vmmap_as_surface` |
| `kv_factorizations.csv` | 36 | Ways to write 35,840 bytes as layers × KV heads × head dimension × bytes (report 18.4) | `kv_layers, kv_heads, head_dim, bytes_per_value, kv_heads_power_of_two, total_layers_if_62_5_percent_have_kv, note` |
| `iosurface_exact_sizes.csv` | 10 | Exact byte size of each IOSurface of 1 MiB or more (report 18.6) | `bytes, mib, snapshots_seen, divisible_by_8192_tokens, bytes_per_token_at_8192, bytes_per_token_at_512` |
| `decode_bucket_fit.csv` | 14 | Decode cost fitted against bucket size and against raw length (report 18.5) | `model, prompt_tokens, mean_x_during_decode, measured_ms_per_token, fitted_ms_per_token` |
| `contention.csv` | 7 | Model speed under CPU memory-bandwidth loads, as percent change against no load (report 19) | `condition, hog_gb_per_s, short_decode_tok_s, short_decode_change_pct, long_decode_4p7k_tok_s, long_decode_change_pct, prefill_2k_ttft_s, prefill_2k_change_pct, prefill_4p7k_ttft_s, prefill_4p7k_change_pct` |
| `ane_bw.csv` | 24 | Core ML matrix-vector time against weight size, by compute unit and weight format (report 20) | `format, units, layers, package_mib, fp16_equiv_mib, weights_millions, median_ms, min_ms, p90_ms, preferred_device_per_op_check` |
| `ifp_reads.csv` | 1,384 | Every 288 KiB read of the expert file in the ten-prompt trace (report 21) | `phase, seconds_into_phase, bytes, offset_low32_bytes` |
| `ifp_cadence_reads.csv` | 423 | The 294,912-byte reads of the 2026-10-25 trace (`data/compare/inspect_ifp_cadence.sh`), geology and long-context prompts; same columns as `ifp_reads.csv`; the raw trace is not included | `phase`, `seconds_into_phase`, `bytes`, `offset_low32_bytes` |
| `ifp_phase_summary.csv` | 10 | Reads, megabytes and distinct offsets per prompt | `phase, output_tokens, seconds, expert_reads, mib_read, distinct_offsets, first_read_s, last_read_s` |
| `ifp_essay_clusters.csv` | 53 | Expert-read clusters of the essay mapped to the text being written (report 21.5) | `seconds_into_phase, reads_in_cluster, text_char_position, next_section_heading, chars_until_that_heading` |
| `essay_headings.csv` | 5 | When each essay section heading was written | `heading, char_position, seconds_into_phase_when_written` |
| `pool_lifetime.csv` | 86 | IOSurface size around one long request (report 18.8) | `seconds_since_start, phase, seconds_since_request_end, iosurface_resident_mib` |
| `spec_blocks.csv` | 127 | Size and spacing of the 10-token delivery blocks by task (report 22) | `task, block_index, tokens_in_block, seconds_since_previous_block` |
| `spec_ms_per_token.csv` | 10 | Milliseconds per token by task, from block spacing | `task, ms_per_token_10_token_blocks, mean_block_gap_ms, blocks, tokens` |
| `spec_temperature.csv` | 12 | Speed under greedy and sampled decoding (report 22.2) | `task, sampling, ms_per_token_run1, ms_per_token_run2` |
| `adapter_switch_cost.csv` | 19 | Latency alternating the general and content-tagging use cases (report 23.4) | `run, use_case, previous_use_case, ttft_s, total_s` |
| `catalog_models.csv` | 3 | The three base-model names exported by Apple's model catalog (report 25, not included); exported names only | `name` |
| `tokenizer_fingerprint.csv` | 10 | Exact-match share of 429 test strings for ten public tokenizers against Apple's token counts, overall and per group (report 27.1) | `tokenizer, exact_match_pct, within_1_token_pct, mean_abs_diff_tokens, apple_over_other_ratio, exact_pct_<group>` |
| `tokenizer_special_tokens.csv` | 59 | Apple and Gemma 3 token counts for special-looking strings (report 27.1) | `string, apple_tokens, gemma3_tokens, gemma3_single_entry, agree` |
| `tokenizer_unused_slots.csv` | 6,242 | Apple's token count for every reserved string `<unusedN>`, N = 0 to 6241 (report 27.1) | `unused_slot_n, apple_tokens` |
| `image_tokens.csv` | 15 | Input tokens of a request with one image, by image size (report 27.2) | `file, width_px, height_px, aspect_ratio, input_tokens_total, image_tokens, image_tokens_minus_3_markers` |
| `evals_summary.csv` | 7 | GSM8K and MMLU spot checks with Wilson intervals (report 27.4) | `benchmark, n, correct, accuracy_pct, ci95_low_pct, ci95_high_pct, guardrail_refusals, note` |
| `evals_gsm8k_items.csv`, `evals_mmlu_items.csv` | 100, 200 | One row per question: gold, prediction, time, error (report 27.4) | `test_index, ..., correct, seconds, error` |
| `chat_template_tokens.csv` | 14 | Billed prompt tokens for message structures of known text length (report 28.2) | `case, prompt_tokens_billed, text_tokens, framing_tokens` |
| `sampling_spread.csv` | 6 | Distinct outputs in repeated runs by sampling setting (report 28.4) | `setting, runs, distinct_outputs` |
| `needle_test.csv` | 36 | Long-context retrieval: prompt length, depth, correct or not (report 28.3) | `target_tokens, prompt_tokens, depth, trial, correct, seconds` |
| `parameter_budget.csv` | 8 | Bytes behind the parameter counts and the weights they hold at the assumed bit width (report 28.1) | `component, bytes, bytes_from, bits_per_weight_assumed, billions_of_weights, note` |
| `same_questions.csv` | 4 | The same 100 GSM8K and 200 MMLU questions through Apple's model and three open models, with Wilson intervals (rounded) and paired counts and exact McNemar p against Apple (report 29) | `model, gsm8k_correct, gsm8k_n, gsm8k_ci_low, gsm8k_ci_high, mmlu_correct, mmlu_n, mmlu_ci_low, mmlu_ci_high, gsm8k_only_model, gsm8k_only_apple, gsm8k_p, mmlu_only_model, mmlu_only_apple, mmlu_p` |

## Notes for plotting

- **Files of reports 27 and 28** are built by `python3 -I data/make_plot_data_card.py` from `data/card_inputs/`. `tokenizer_special_tokens.csv` and the eval CSV
  files come from `data/card_inputs/special_tokens_compare.py` and `evals_report.py` (they need the `tokenizers` package and the saved eval results).

- **Token counts**: `tokenizer_*` files already subtract the 1-token overhead that `fm count-tokens` adds.
  `ctx_profile.csv` uses counts as printed by `count-tokens` (prompt only, overhead included).
- **`power_samples.csv`, `phase` blank**: sample falls outside a labeled phase (warm-up, gaps between phases).
  The phase `image_invalid` is not a valid image run: the test image could not be written (output folder owned by root).
  CPU power is system-wide and includes the processes that ran the measurement. ANE and GPU power belong to the workload.
- **`power_samples.csv` timestamps** have one-second resolution, so up to four samples share a `local_time`.
  Order rows by file order, not by time.
- **`ctx_profile.csv`, `output_is_counting_task = 0`**: at 5,901 and 6,881 tokens the model did not stop after the
  count and wrote the filler sentence over and over. Exclude those rows from decode-speed fits, as the report does.
- **`memory_by_region_type.csv`** comes from `vmmap -v` with every split shared-cache library listed, so total
  resident includes pages shared with the whole system. Use `dirty_bytes` and `region_type == IOSurface` for the
  process's own cost.
- **Hand-typed series** (`context_limit_probe.csv`, `api_cache_tests.csv`, `image_latency.csv`) were copied from
  command output printed during the run. The generating commands are in the report.
- **Scale run** (`scale_run.csv`): the 7,570-token row ended early with a guardrail error, so its peak is the pool
  retained from earlier requests. Pass 2 rows all show the retained 8,192 pool. Use pass 1 for the step curve.
