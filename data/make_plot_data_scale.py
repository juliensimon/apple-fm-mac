#!/usr/bin/env python3
"""Plot-ready CSV files for the scale run (section 18). Reads data/scale_run_2026-10-24 and data/plots; no fm calls."""
import csv, os, statistics as st
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "plots")
KV = lambda B: 2 * 35840 * B / 2**20


def write(name, header, rows):
    with open(os.path.join(P, name), "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)
    print(f"{name}: {len(rows)} rows")


BUCKETS = (512, 1024, 2048, 4096, 8192)
bucket = lambda x: next(b for b in BUCKETS if x <= b)
TEMPLATE = 56

rows = []
for r in csv.DictReader(open(os.path.join(HERE, "scale_run_2026-10-24", "scale_summary.tsv")), delimiter="\t"):
    n = int(r["prompt_tokens"]); peak = float(r["peak_iosurface_resident_mib"]); b = bucket(n - 1 + TEMPLATE)
    pred = 406.6 if b == 512 else 406.6 + KV(b)
    rows.append([r["pass"], r["reps"], n, n - 1 + TEMPLATE, b, r["wall_seconds"], peak, round(pred, 1), round(peak - pred, 1), r["vmmap_samples"]])
write("scale_run.csv", ["pass", "reps", "counted_prompt_tokens", "effective_tokens_assumed_template_56", "bucket", "wall_seconds", "peak_iosurface_resident_mib", "model_fixed_plus_kv_pair_mib", "error_mib", "vmmap_samples"], rows)

write("kv_pair_by_bucket.csv", ["bucket_tokens", "bytes_per_tensor", "mib_per_tensor", "mib_k_plus_v_pair", "seen_in_vmmap_as_surface"],
      [[B, 35840 * B, round(35840 * B / 2**20, 3), round(KV(B), 3), "yes" if B in (512, 8192) else "inferred from step"] for B in BUCKETS])

sols = []
for L in (7, 10, 14, 20, 28, 35, 40, 56, 70, 140):
    for kvh in (1, 2, 4, 5, 8, 10, 16, 20, 40):
        for hd in (64, 128, 256):
            for by in (1, 2):
                if L * kvh * hd * by == 35840:
                    pow2 = int(kvh in (1, 2, 4, 8, 16))
                    sols.append([L, kvh, hd, by, pow2, round(L / 0.625, 1), "natural" if (L, kvh, hd, by) == (35, 8, 128, 1) else ""])
write("kv_factorizations.csv", ["kv_layers", "kv_heads", "head_dim", "bytes_per_value", "kv_heads_power_of_two", "total_layers_if_62_5_percent_have_kv", "note"], sols)

io = [r for r in csv.DictReader(open(os.path.join(P, "iosurface_regions.csv"))) if r["pid"] == "9704"]
seen = {}
for r in io:
    v = int(r["virtual_bytes"])
    if v >= 2**20: seen.setdefault(v, set()).add(r["snapshot"])
write("iosurface_exact_sizes.csv", ["bytes", "mib", "snapshots_seen", "divisible_by_8192_tokens", "bytes_per_token_at_8192", "bytes_per_token_at_512"],
      [[v, round(v / 2**20, 3), "+".join(sorted(s)), int(v % 8192 == 0), v // 8192 if v % 8192 == 0 else "", v // 512 if v % 512 == 0 else ""] for v, s in sorted(seen.items(), reverse=True)])

prof = [r for r in csv.DictReader(open(os.path.join(P, "ctx_profile.csv"))) if r["output_is_counting_task"] == "1"]
by = {}
for r in prof: by.setdefault(int(r["prompt_tokens"]), []).append(float(r["ms_per_token"]))
pts = [(n, st.mean(v)) for n, v in sorted(by.items())]
def meanB(n, F, mode):
    eff0 = n - 1 + F; L = [eff0 + t for t in range(1, 173)]
    return float(np.mean([bucket(x) for x in L])) if mode == "bucket" else float(np.mean(L))
out = []
for mode in ("bucket", "length"):
    xs = [meanB(n, TEMPLATE, mode) for n, _ in pts]; ys = [m for _, m in pts]
    c, a = np.polyfit(xs, ys, 1)
    for (n, m), x in zip(pts, xs): out.append([mode, n, round(x, 1), round(m, 3), round(a + c * x, 3)])
write("decode_bucket_fit.csv", ["model", "prompt_tokens", "mean_x_during_decode", "measured_ms_per_token", "fitted_ms_per_token"], out)
