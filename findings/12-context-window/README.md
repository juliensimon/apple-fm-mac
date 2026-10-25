# 12. The context window

**In the article:** no, repository only. **Basis:** Measured; Apple says (8,192). **Date:** 2026-10-24. **Machine:** MacBook Pro, Apple M3 Max (Mac15,9), 48 GB, macOS 27.0.1 (build 26A434).

## Hypothesis

Question: How large is the context window in practice?

No hypothesis was written before this test.

## Experiment

Query the public API for the reported limits; send prompts of increasing length near the limit.

From the repository root:

```
swiftc -O -parse-as-library data/public_api_query.swift -o runs/public_api_query && runs/public_api_query
```

Files:

- `data/plots/context_limit_probe.csv`
- `data/public_api_query.swift`

## Results

- The public API reports Core Advanced, an 8,192-token window, vision, guided generation and tool calling, and no reasoning mode.
- A prompt of 8,102 tokens worked; 8,158 failed.

## Conclusion

The public API reports an 8,192-token window, and a prompt just under it works.

What it does not show:

- The probe counts prompt tokens with Apple's counter; the space left for the answer is not separated.
