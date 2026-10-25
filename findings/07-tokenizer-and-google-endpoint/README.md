# 07. Tokenizer, Google's endpoint and the six descriptions

**In the article:** yes. **Basis:** Measured. **Date:** 2026-10-24. **Machine:** MacBook Pro, Apple M3 Max (Mac15,9), 48 GB, macOS 27.0.1 (build 26A434).

## Hypothesis

Question: Whose tokenizer does Apple's model use?

No hypothesis was written before this test.

## Experiment

Count 429 strings with Apple's `fm count-tokens`, with twelve open tokenizers and with Google's `countTokens` endpoint (257 public strings); compare counts string by string.

From the repository root:

```
python scripts/tokenizer_test.py data/tokenizer_test/strings_public.csv
python3 data/gemini_counttokens.py   # needs GEMINI_API_KEY
python scripts/charts/make_charts.py
python scripts/charts/table.py data/tables.json plots/
python3 scripts/check_numbers.py
```

Files:

- `data/tokenizer_test/`
- `data/tokenizer_fingerprint.csv`
- `data/fingerprint_google.json`
- `data/gemini_counttokens.json`
- `data/card_inputs/fingerprint_google_diff.json`
- `data/plots/iosurface_exact_sizes.csv`
- `plots/tokenizer-match.png`
- `plots/six-sentences.png`

## Results

- 429 strings: Gemma 3's tokenizer matches Apple's count on 429 of 429. Gemma 3n 100%, Gemma 4 99.1% (it differs on four strings with `<h1>` or `<h2>`), Gemma 2 75.5%, eight tokenizers from other labs 20.7% to 44.5%.
- Google's `countTokens` endpoint returned Apple's count on all 257 public strings, under four model names.
- A 192 MiB memory surface is 262,144 x 768 bytes; 262,144 is the size of Gemma 3's vocabulary.
- `plots/six-sentences.png`: six published descriptions of Google's role, quoted, with their sources in the article.

## Conclusion

Apple's token counter gives Gemma 3's count on every string tested, and Google's own counting endpoint gives Apple's count on every string sent.

What it does not show:

- A shared tokenizer shows nothing about weights, training data or architecture.
- 172 of the 429 strings are private and not published; the 257 public ones are in `data/tokenizer_test/strings_public.csv`.
