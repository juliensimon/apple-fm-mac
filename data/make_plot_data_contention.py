#!/usr/bin/env python3
"""contention.json -> plots/contention.csv (percent change against the first no-load run)."""
import csv, json, os, statistics as st
HERE = os.path.dirname(os.path.abspath(__file__))
res = json.load(open(os.path.join(HERE, "contention.json")))
def m(xs): return st.mean(x for x in xs if x is not None)
base = res[0]
b_short = m([r["tok_s"] for r in base["short_decode"]]); b_long = m([r["tok_s"] for r in base["long_decode"]])
b_pre = m([r["ttft_s"] for r in base["prefill_2k"]]); b_lttft = m([r["ttft_s"] for r in base["long_decode"]])
rows = []
for r in res:
    sh = m([x["tok_s"] for x in r["short_decode"]]); lo = m([x["tok_s"] for x in r["long_decode"]])
    pf = m([x["ttft_s"] for x in r["prefill_2k"]]); lt = m([x["ttft_s"] for x in r["long_decode"]])
    rows.append([r["condition"], r["hog_gbps_during"] if r["hog_gbps_during"] is not None else 0, round(sh, 2), round((sh / b_short - 1) * 100, 1),
                 round(lo, 2), round((lo / b_long - 1) * 100, 1), round(pf, 3), round((pf / b_pre - 1) * 100, 1), round(lt, 3), round((lt / b_lttft - 1) * 100, 1)])
with open(os.path.join(HERE, "plots", "contention.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["condition", "hog_gb_per_s", "short_decode_tok_s", "short_decode_change_pct", "long_decode_4p7k_tok_s", "long_decode_change_pct",
                "prefill_2k_ttft_s", "prefill_2k_change_pct", "prefill_4p7k_ttft_s", "prefill_4p7k_change_pct"])
    w.writerows(rows)
for r in rows: print(r)
