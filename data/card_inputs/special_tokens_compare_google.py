#!/usr/bin/env python3
"""Apple's token counts for the 59 special-looking strings against Gemma 3, Gemma 3n and Gemma 4. Prints agreement and the strings where Gemma 3 and Gemma 4 differ.
Run: uv run --with tokenizers python data/card_inputs/special_tokens_compare_google.py   (writes special_tokens_gemma3_vs_gemma4.json)"""
import json
import os
from tokenizers import Tokenizer

os.chdir(os.path.dirname(os.path.abspath(__file__)))   # the paths below are relative to this folder
special = json.load(open("apple_special.json"))
toks = {"Gemma 3": Tokenizer.from_pretrained("unsloth/gemma-3-4b-it"), "Gemma 3n E4B": Tokenizer.from_pretrained("unsloth/gemma-3n-E4B-it"),
        "Gemma 4 E4B": Tokenizer.from_pretrained("unsloth/gemma-4-E4B-it-unsloth-bnb-4bit")}
n = lambda t, s: len(t.encode(s, add_special_tokens=False).ids)
for name, t in toks.items():
    ag = sum(1 for s, a in special.items() if n(t, s) == a)
    print(f"{name:14s} agrees with Apple on {ag} of {len(special)} special strings")
print("\nstrings where Gemma 3 agrees with Apple and Gemma 4 does not:")
rows = []
for s, a in special.items():
    g3, g4 = n(toks["Gemma 3"], s), n(toks["Gemma 4 E4B"], s)
    if g3 == a and g4 != a:
        print(f"  {s!r}: apple {a}, gemma3 {g3}, gemma4 {g4}"); rows.append([s, a, g3, g4])
json.dump(rows, open("special_tokens_gemma3_vs_gemma4.json", "w"), indent=1)
v4 = toks["Gemma 4 E4B"].get_vocab()
print("\nGemma 4 vocab has these as single entries:", [s for s in ["<start_of_turn>", "<end_of_turn>", "<start_of_image>", "<end_of_image>", "<mask>", "<table>", "<h1>", "<div>", "<unused0>", "<unused99>"] if s in v4])
v3 = toks["Gemma 3"].get_vocab()
print("Gemma 3 vocab has these as single entries:", [s for s in ["<start_of_turn>", "<end_of_turn>", "<start_of_image>", "<end_of_image>", "<mask>", "<table>", "<h1>", "<div>", "<unused0>", "<unused99>"] if s in v3])
