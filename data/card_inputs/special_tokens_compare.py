#!/usr/bin/env python3
"""Compare Apple's token counts for special-looking strings (measured with `fm count-tokens`, minus its 1-token offset)
with Gemma 3's public tokenizer. Writes ../plots/tokenizer_special_tokens.csv (REPORT 27.1).
The second part compared an early probe of selected reserved slots (apple_unused_map.json, not kept); the full scan of all 6,242
slots replaced it (scan_unused.py, unused_scan_full.json, make_plot_data_card.py), so that part runs only if the probe file exists.
Run: uv run --with tokenizers python data/card_inputs/special_tokens_compare.py"""
import csv, json, os
from tokenizers import Tokenizer

os.chdir(os.path.dirname(os.path.abspath(__file__)))   # the paths below are relative to this folder
OUT = os.path.join("..", "plots", "tokenizer_special_tokens.csv")
t = Tokenizer.from_pretrained("unsloth/gemma-3-4b-it")      # public copy of Gemma 3's tokenizer
vocab = t.get_vocab()
special = json.load(open("apple_special.json"))

with open(OUT, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["string", "apple_tokens", "gemma3_tokens", "gemma3_single_entry", "agree"])
    for s, n in special.items():
        g = len(t.encode(s, add_special_tokens=False).ids)
        w.writerow([s, n, g, s in vocab, n == g])
print("Gemma 3 vocab entries (HF-reported):", t.get_vocab_size())
rows = list(csv.DictReader(open(OUT)))
print(len(rows), "strings; agree on", sum(r["agree"] == "True" for r in rows))
for r in rows:
    if r["agree"] != "True": print("  differs:", r)
if os.path.exists("apple_unused_map.json"):
    unused = json.load(open("apple_unused_map.json"))["probes"]
    with open("tokenizer_unused_slots_probe.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["slot", "string", "gemma3_has_entry", "apple_single_token"])
        for k, v in sorted(unused.items(), key=lambda kv: int(kv[0])):
            s = f"<unused{k}>"
            w.writerow([k, s, s in vocab, v])
    last = max(int(k) for k in unused if f"<unused{k}>" in vocab)
    print("largest tested slot that exists in Gemma 3:", last)
print("<unused6241> in Gemma 3:", "<unused6241>" in vocab, "| <unused6242> in Gemma 3:", "<unused6242>" in vocab)
print("Gemma 3 total <unusedN> entries:", sum(1 for k in vocab if k.startswith("<unused") and k.endswith(">")))
