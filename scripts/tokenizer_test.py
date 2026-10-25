#!/usr/bin/env python3
"""The tokenizer test on your own strings: Apple's token count for each string, from `fm count-tokens -q`, against the counts of
public tokenizers. A match is an equal count. Prints the share of exact matches per tokenizer and writes the per-string counts.

Apple's count: `fm count-tokens -q -- <text>` prints one token more than the text alone (REPORT 4.3); that one token is subtracted,
as in the run of 2026-10-24 (data/card_inputs/apple_counts.py). Public tokenizers: the Hugging Face `tokenizers` library with
special tokens off, and OpenAI's tiktoken for GPT-4 and GPT-4o, from the same sources as the published run.

Input: a CSV file with a `text` column (other columns such as id, category or apple_fm are used if present), or a plain text
file with one string per line (blank lines skipped).
Output: a CSV with id, category, characters and one count column per tokenizer. Your strings are not copied into it unless
you pass --keep-text.

Run: uv run --with tokenizers --with tiktoken python scripts/tokenizer_test.py my_strings.txt --out runs/my_counts.csv
     uv run --with tokenizers --with tiktoken python scripts/tokenizer_test.py data/tokenizer_test/strings_public.csv --reuse-apple
(--reuse-apple takes Apple's counts from the file's apple_fm column instead of calling fm, so it also runs on a machine without fm.)
The first run downloads each tokenizer file from the Hugging Face Hub.
"""
import argparse
import csv
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

# (column, label, source): the fifteen tokenizers of data/tokenizer_test/counts_all_429.csv, same order and same sources
TOKENIZERS = [
    ("gemma3", "Gemma 3", "unsloth/gemma-3-4b-it"),
    ("gemma3n_e4b", "Gemma 3n E4B", "unsloth/gemma-3n-E4B-it"),
    ("gemma3n_e2b", "Gemma 3n E2B", "unsloth/gemma-3n-E2B-it"),
    ("gemma4_e4b", "Gemma 4 E4B", "unsloth/gemma-4-E4B-it-unsloth-bnb-4bit"),
    ("gemma4_e2b", "Gemma 4 E2B", "unsloth/gemma-4-E2B-it-unsloth-bnb-4bit"),
    ("gemma4_26b_a4b", "Gemma 4 26B-A4B", "unsloth/gemma-4-26B-A4B-it-NVFP4"),
    ("gemma2", "Gemma 2", "unsloth/gemma-2-2b"),
    ("mistral_nemo", "Mistral Nemo", "mistralai/Mistral-Nemo-Instruct-2407"),
    ("qwen2_5", "Qwen 2.5", "Qwen/Qwen2.5-0.5B"),
    ("gpt4o_o200k", "GPT-4o (o200k)", "tiktoken:o200k_base"),
    ("deepseek_v3", "DeepSeek V3", "deepseek-ai/DeepSeek-V3"),
    ("llama3_1", "Llama 3.1", "NousResearch/Meta-Llama-3.1-8B"),
    ("gpt4_cl100k", "GPT-4 (cl100k)", "tiktoken:cl100k_base"),
    ("gpt2", "GPT-2", "openai-community/gpt2"),
    ("phi3_5_mini", "Phi-3.5 mini", "microsoft/Phi-3.5-mini-instruct"),
]
ENV = dict(os.environ, NO_COLOR="1", TERM="dumb")


def read_strings(path):
    """Rows of {id, category, text, apple_fm?} from a CSV with a text column, or from a text file with one string per line."""
    p = Path(path)
    if p.suffix.lower() == ".csv":
        rows = list(csv.DictReader(open(p, newline="", encoding="utf-8")))
        if not rows or "text" not in rows[0]:
            sys.exit(f"{p}: a CSV input needs a 'text' column")
        return [{"id": r.get("id") or str(i + 1), "category": r.get("category", ""), "text": r["text"], "apple_fm": r.get("apple_fm", "")}
                for i, r in enumerate(rows)]
    lines = [l.rstrip("\n") for l in open(p, encoding="utf-8")]
    return [{"id": str(i + 1), "category": "", "text": l, "apple_fm": ""} for i, l in enumerate(x for x in lines if x.strip())]


def apple_count(text, offset):
    r = subprocess.run(["fm", "count-tokens", "-q", "--", text], capture_output=True, text=True, env=ENV, stdin=subprocess.DEVNULL, timeout=120)
    try:
        return int(r.stdout.strip()) - offset
    except ValueError:
        return None


def counter(source):
    if source.startswith("tiktoken:"):
        import tiktoken
        enc = tiktoken.get_encoding(source.split(":", 1)[1])
        return lambda s: len(enc.encode_ordinary(s))
    from tokenizers import Tokenizer
    t = Tokenizer.from_pretrained(source)
    return lambda s: len(t.encode(s, add_special_tokens=False).ids)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("strings", help="CSV with a text column, or a text file with one string per line")
    ap.add_argument("--out", default="runs/tokenizer_test_counts.csv", help="per-string counts (default: %(default)s)")
    ap.add_argument("--reuse-apple", action="store_true", help="take Apple's counts from the apple_fm column instead of calling fm")
    ap.add_argument("--offset", type=int, default=1, help="tokens fm count-tokens adds to any text (default: %(default)s)")
    ap.add_argument("--tokenizers", default="", help="comma-separated columns to run, e.g. gemma3,gemma2,gpt4o_o200k (default: all)")
    ap.add_argument("--keep-text", action="store_true", help="copy each string into the output CSV")
    a = ap.parse_args()

    rows = read_strings(a.strings)
    if not rows:
        sys.exit("no strings")
    if a.reuse_apple:
        if any(r["apple_fm"] == "" for r in rows):
            sys.exit("--reuse-apple needs an apple_fm value on every row")
        for r in rows:
            r["apple_fm"] = int(r["apple_fm"])
    else:
        try:
            subprocess.run(["fm", "--help"], capture_output=True, stdin=subprocess.DEVNULL, timeout=60)
        except FileNotFoundError:
            sys.exit("`fm` not found: this needs macOS 27 with Apple Intelligence on (or use --reuse-apple with an apple_fm column)")
        for n, r in enumerate(rows, 1):
            r["apple_fm"] = apple_count(r["text"], a.offset)
            if n % 50 == 0:
                print(f"fm count-tokens: {n}/{len(rows)}", flush=True)
        failed = sum(r["apple_fm"] is None for r in rows)
        if failed:
            print(f"warning: fm count-tokens gave no number for {failed} strings; they are left out of the shares", flush=True)

    wanted = [t for t in TOKENIZERS if not a.tokenizers or t[0] in a.tokenizers.split(",")]
    used = []
    for col, label, source in wanted:
        try:
            f = counter(source)
        except Exception as e:
            print(f"skip {label}: {str(e)[:100]}", flush=True)
            continue
        for r in rows:
            r[col] = f(r["text"])
        used.append((col, label))

    scored = [r for r in rows if r["apple_fm"] is not None]
    cats = sorted({r["category"] for r in scored if r["category"]})
    print(f"\n{len(scored)} strings with an Apple count")
    print(f"{'tokenizer':18s} {'exact':>7s} {'within 1':>9s} {'mean abs diff':>14s}" + "".join(f"  {c[:14]:>14s}" for c in cats))
    for col, label in sorted(used, key=lambda cl: -sum(r[cl[0]] == r["apple_fm"] for r in scored)):
        d = [r[col] - r["apple_fm"] for r in scored]
        per = defaultdict(list)
        for r in scored:
            per[r["category"]].append(r[col] == r["apple_fm"])
        line = f"{label:18s} {100 * sum(x == 0 for x in d) / len(d):6.1f}% {100 * sum(abs(x) <= 1 for x in d) / len(d):8.1f}% {sum(abs(x) for x in d) / len(d):14.2f}"
        print(line + "".join(f"  {100 * sum(per[c]) / len(per[c]):13.1f}%" for c in cats))

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cols = ["id", "category", "characters"] + (["text"] if a.keep_text else []) + ["apple_fm"] + [c for c, _ in used]
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in rows:
            r["characters"] = len(r["text"])
            w.writerow([r.get(c, "") if r.get(c) is not None else "" for c in cols])
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
