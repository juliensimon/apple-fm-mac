#!/usr/bin/env python3
"""CSV files for the model card and the repository-style files, built from data/card_inputs/:
tokenizer fingerprint, reserved-slot map, image token cost, chat-template token accounting, sampling spread,
long-context retrieval, parameter and memory budget."""
import csv, json, os

HERE = os.path.dirname(os.path.abspath(__file__)); P = os.path.join(HERE, "plots"); C = os.path.join(HERE, "card_inputs")


def write(name, header, rows):
    with open(os.path.join(P, name), "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)
    print(f"{name}: {len(rows)} rows")


# ---- tokenizer fingerprint -----------------------------------------------------------------------------------------------
fp = json.load(open(os.path.join(C, "fingerprint.json")))
cats = ["english prose", "english report text", "multilingual", "code", "numbers urls emoji", "rare words"]
write("tokenizer_fingerprint.csv", ["tokenizer", "exact_match_pct", "within_1_token_pct", "mean_abs_diff_tokens", "apple_over_other_ratio"] + [f"exact_pct_{c.replace(' ', '_')}" for c in cats],
      [[n, round(r["exact"] * 100, 1), round(r["within1"] * 100, 1), round(r["mae"], 2), round(r["ratio"], 3)] + [round(r["per"][c]["exact"] * 100, 1) for c in cats]
       for n, r in sorted(fp.items(), key=lambda kv: -kv[1]["exact"])])

# ---- reserved slots: every <unusedN>, N = 0 to 6241 -----------------------------------------------------------------------
scan = {int(k): v for k, v in json.load(open(os.path.join(C, "unused_scan_full.json"))).items()}
write("tokenizer_unused_slots.csv", ["unused_slot_n", "apple_tokens"], [[n, scan[n]] for n in sorted(scan)])

# ---- image token cost --------------------------------------------------------------------------------------------------
SIZES = {"i64": (64, 64), "i128": (128, 128), "i256": (256, 256), "i512": (512, 512), "i768": (768, 768), "i1024": (1024, 1024), "i2048": (2048, 2048),
         "big4000": (4000, 4000), "tall100x300": (100, 300), "wide300x100": (300, 100), "w1024x256": (1024, 256), "pano4000x1000": (4000, 1000),
         "ocr_en": (897, 338), "qr": (372, 372), "ocr_small": (329, 108)}   # pixel sizes read with `sips` from the generated files
tsv = [l.split("\t") for l in open(os.path.join(C, "image_tokens.tsv")).read().splitlines()]
base = int([t for n, t in tsv if n == "none"][0])
rows = []
for n, t in tsv:
    if n == "none": continue
    key = os.path.basename(n).removesuffix(".png"); w, h = SIZES[key]; cost = int(t) - base
    rows.append([os.path.basename(n), w, h, round(max(w, h) / min(w, h), 2), int(t), cost, cost - 3])
write("image_tokens.csv", ["file", "width_px", "height_px", "aspect_ratio", "input_tokens_total", "image_tokens", "image_tokens_minus_3_markers"], rows)

# ---- chat template accounting, sampling spread -----------------------------------------------------------------------------
tp = json.load(open(os.path.join(C, "template_probe.json")))
write("chat_template_tokens.csv", ["case", "prompt_tokens_billed", "text_tokens", "framing_tokens"],
      [[s["case"], s["prompt_tokens"], sum(s["text_tokens_each"]), s["prompt_tokens"] - sum(s["text_tokens_each"])] for s in tp["structures"]])
write("sampling_spread.csv", ["setting", "runs", "distinct_outputs"], [[s["setting"], s["runs"], s["distinct"]] for s in tp["sampling"]])

# ---- long-context retrieval ---------------------------------------------------------------------------------------------------
nd = json.load(open(os.path.join(C, "needle.json")))
write("needle_test.csv", ["target_tokens", "prompt_tokens", "depth", "trial", "correct", "seconds"],
      [[r["target_tokens"], r["prompt_tokens"], r["depth"], r["trial"], r["correct"], r["seconds"]] for r in nd])

# ---- parameter and memory budget -----------------------------------------------------------------------------------------------
PAGE = 16384
EXPERT = 294912
rows = [
    ["routed-expert store (ifp_rasterized_weights.bin)", 4948197376, "file size", "2", 4948197376 * 8 / 2 / 1e9, "16,775 units + 1 MiB, or 16,778 units + 160 KiB; 1,179,648 weights per unit at 2 bits"],
    ["always-resident ANE model pages (log: 40,680 pages)", 40680 * PAGE, "ANE client log x 16 KiB", "2", 40680 * PAGE * 8 / 2 / 1e9, "upper bound: includes any program code and metadata in the pages"],
    ["embedding table (persistent IOSurface)", 201326592, "vmmap surface size", "4 (hidden 1,536) or 2 (hidden 3,072)", 262144 * 1536 / 1e9, "262,144 rows x 768 bytes; 0.40 billion at 4 bits and 1,536 values, 0.81 billion at 2 bits and 3,072 values"],
    ["draft model ANE pages (log: 575 pages)", 575 * PAGE, "ANE client log x 16 KiB", "2", 575 * PAGE * 8 / 2 / 1e9, "upper bound"],
    ["safety model 300M ANE pages (log: 11,611 pages)", 11611 * PAGE, "ANE client log x 16 KiB", "5.07 if exactly 300M weights", 0.3, "weights taken from the model name; the bit width follows from the page count"],
    ["expert slots, mutable weights buffer", 30081024, "mapping size", "2", 30081024 * 8 / 2 / 1e9, "exactly 102 expert units"],
    ["expert-sized buffer (IOKit neural region)", 371736576, "mapping size", "2", 371736576 * 8 / 2 / 1e9, "1,260.5 expert units; likely the expert cache"],
    ["routed experts selected per prompt (150 to 230 units)", 150 * EXPERT, "expert-file reads in the first 0.2 s", "2", 150 * EXPERT * 8 / 2 / 1e9, "low end; the high end is 230 units, 0.27 billion"],
]
write("parameter_budget.csv", ["component", "bytes", "bytes_from", "bits_per_weight_assumed", "billions_of_weights", "note"],
      [[r[0], r[1], r[2], r[3], round(r[4], 3), r[5]] for r in rows])
