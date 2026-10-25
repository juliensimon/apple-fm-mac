# 01. The model card

**In the article:** yes. **Basis:** Mixed; each line of the card carries its own label. **Date:** 2026-10-24 to 2026-10-25. **Machine:** MacBook Pro, Apple M3 Max (Mac15,9), 48 GB, macOS 27.0.1 (build 26A434).

## Hypothesis

Question: What does a model card for Core Advanced look like when every line has to say where it comes from?

No hypothesis was written before this test.

## Experiment

Collect the facts from the other items and from Apple's pages; give each line one basis label; render the table.

From the repository root:

```
python3 scripts/charts/table.py data/tables.json plots/
```

Files:

- `data/tables.json`
- `plots/core-advanced-card.png`

## Results

- The card is `plots/core-advanced-card.png`, built from the `core-advanced-card` entry of `data/tables.json` by `scripts/charts/table.py`.
- Sections: identity, architecture (layers, hidden size, experts, routing, attention, context, vocabulary), compression, runtime on a Mac, training and use. Labels: **Apple says**, **Apple staff** (answers on Apple's forums), **measured** (with the item named), **inferred** (arithmetic or reading from measurements), **reported** (the press briefing), **Apple paper** (Stepped MoE, arXiv 2610.07348, which does not name the model).
- Attention: the measured cache (35,840 bytes a token for each of K and V) cannot fit the paper's twelve KV heads; 35 layers x 8 KV heads x 128 x 1 byte fits, as do 70 x 4 x 128 x 1 and 35 x 4 x 128 x 2 (item 16).
- Each measured or inferred line points to the item in this folder that holds its data.

## Conclusion

One table that gives the facts about Apple's on-device model, Core Advanced, in the order of a Hugging Face model card, each line labeled with where it comes from.

What it does not show:

- The card holds no number that is not in another item; it is an index, not a measurement.
