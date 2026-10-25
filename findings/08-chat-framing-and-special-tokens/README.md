# 08. Chat framing and special tokens

**In the article:** yes. **Basis:** Measured. **Date:** 2026-10-24. **Machine:** MacBook Pro, Apple M3 Max (Mac15,9), 48 GB, macOS 27.0.1 (build 26A434).

## Hypothesis

Question: Does Apple's chat framing match Gemma 3's, and are Gemma 3's special tokens unchanged?

No hypothesis was written before this test.

## Experiment

Count the framing tokens `fm serve` adds to a message; count each reserved and special token with Apple's counter and with Gemma 3's tokenizer.

From the repository root:

```
python3 data/card_inputs/template_probe.py   # needs fm serve
python3 data/card_inputs/scan_unused.py
python3 scripts/check_numbers.py
```

Files:

- `data/plots/chat_template_tokens.csv`
- `data/card_inputs/template_probe.json`
- `data/plots/tokenizer_special_tokens.csv`
- `data/plots/tokenizer_unused_slots.csv`
- `data/card_inputs/unused_scan_full.json`
- `data/card_inputs/apple_special.json`

## Results

- One user message costs 55 tokens of framing in `fm serve`; Gemma 3's chat template explains 9.
- Of 6,242 reserved placeholder slots (`<unusedN>`), 775 no longer count as one token.

## Conclusion

The chat markers count as single tokens, as in Gemma 3, but Apple's framing of a message is longer than Gemma 3's template explains, and part of the reserved token range has changed.

What it does not show:

- `template_probe.py` includes five prompts that ask the model to repeat its hidden framing text (disclosed in the README).
