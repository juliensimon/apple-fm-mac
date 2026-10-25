# 11. How `fm serve` behaves

**In the article:** no, repository only. **Basis:** Measured. **Date:** 2026-10-24. **Machine:** MacBook Pro, Apple M3 Max (Mac15,9), 48 GB, macOS 27.0.1 (build 26A434).

## Hypothesis

Question: How close is `fm serve` to the chat-completions protocol that clients expect?

No hypothesis was written before this test.

## Experiment

Send requests with each parameter a client would use and record what comes back; repeat one long prompt to test for a prefix cache.

From the repository root:

```
python3 data/api2.py   # needs fm serve
python3 data/compare/probe_max_tokens.py
python3 data/api.py   # needs fm serve
```

Files:

- `data/compare/probe_max_tokens.jsonl`
- `data/plots/api_cache_tests.csv`

## Results

- It streams by default, ignores `max_tokens` (73 tokens with and without it), honors `max_completion_tokens` loosely (10 tokens for a limit of 5), rejects `stop` and `n`, takes `json_schema`, and returns tool arguments as text.
- No prefix cache: the same 2,024-token prompt took 1.41 s on every repeat after the first (2.01 s).

## Conclusion

`fm serve` speaks the chat-completions protocol with differences that matter to a client, and keeps no prefix cache.

What it does not show:

- macOS 27.0.1 only; the server may change with any release.
