#!/bin/bash
# Does the model load experts from its weight file while it works? A file-activity trace for different prompts.
#
# Run:   sudo bash inspect_ifp.sh
# Takes: about 4 minutes. Writes to ./ifp_out/ next to this script.
#
# Apple's model page says the model "selects a fixed set of experts during initial processing, periodically
# reselecting them during generation", with the full model stored in flash. The weight file model.od is open on
# a file descriptor of the main inference provider. If experts are read from it, `pread` calls on that descriptor
# will show up in fs_usage with an offset (O=) and a size (B=).
#
# What it records: names of system calls, file descriptors, offsets and sizes of reads (fs_usage, filesystem and
# pager classes), for the main provider process only, while a fixed list of prompts runs: code, math, French,
# Japanese, biology, extraction, a content-tagging use case, and one long essay that changes topic five times.
# What it does not record: the contents of any read. No memory is read, no debugger, no change to any setting.

set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/ifp_out"
USER_NAME="${SUDO_USER:-$(logname)}"
if [ "$(id -u)" -ne 0 ]; then echo "run with sudo"; exit 1; fi
mkdir -p "$OUT"; chown "$USER_NAME" "$OUT"; cd "$OUT" || exit 1
export NO_COLOR=1
as_user() { sudo -u "$USER_NAME" env NO_COLOR=1 "$@"; }
mark() { echo "$(date +%s.%N) $*" >> phases.txt; }

echo "[1/4] warm the model"
as_user fm respond --no-stream -g -- 'Reply with the single word OK.' > /dev/null 2>&1
sleep 1
MAIN="$(ps -axo pid=,rss=,command= | grep 'TGOnDeviceInferenceProviderService.appex' | grep -v grep | sort -k2 -n -r | head -1 | awk '{print $1}')"
echo "main provider pid: $MAIN" | tee main_pid.txt
lsof -p "$MAIN" -n -P 2>/dev/null | grep -E 'model\.od|\.odix|ifp_' > fd_map.txt
cat fd_map.txt | cut -c1-200

echo "[2/4] start fs_usage on the provider"
fs_usage -w -f filesys -f pager "$MAIN" > fs_ifp.txt 2>&1 &
FU=$!
sleep 1

run() {
  label="$1"; shift
  mark "start_$label"
  as_user fm respond --no-stream -g "$@" > "out_$label.txt" 2>&1 < /dev/null
  mark "end_$label"
  sleep 1.5
}

echo "[3/4] prompts"
run code        -- 'Write a Python function that merges two sorted lists, with three unit tests.'
run math        -- 'Prove that the square root of 2 is irrational. Be rigorous.'
run french      -- "Rédige un court poème sur l'automne, en français, de huit vers."
run japanese    -- '日本語で、東京の観光名所を五つ、短い説明つきで紹介してください。'
run biology     -- 'Explain how the Krebs cycle works, step by step.'
run extraction  -- 'Extract the vendor, date and amount as three lines: Invoice from Acme Corp on 12 March 2026 for 1,284.50 EUR.'
run tagging     --use-case content-tagging -- 'Tag the topics: The new GPU doubles inference throughput for small language models on laptops.'
run hamlet      -- 'Summarize the plot of Hamlet in three sentences.'
run essay       -- 'Write a very long essay, at least 1500 words, that moves through these five topics in this order: black holes, sourdough baking, contract law, the history of jazz, and marine biology. Do not stop early and do not summarize.'
run repeat      -- 'Write the sentence "The cat sat on the mat." exactly 200 times, one per line.'

echo "[4/4] stop and summarize"
kill "$FU" 2>/dev/null; wait "$FU" 2>/dev/null
lsof -p "$MAIN" -n -P 2>/dev/null | grep -E 'model\.od|\.odix|ifp_' > fd_map_after.txt
{
  echo "## syscall counts"; awk '{print $2}' fs_ifp.txt | sort | uniq -c | sort -rn | head -25
  echo; echo "## reads by file descriptor (op fd count)"
  grep -aE ' (pread|read|PgIn|PAGE_IN_FILE|RdData)' fs_ifp.txt | awk '{op=$2; fd="-"; for(i=3;i<=NF;i++) if($i ~ /^F=/) fd=$i; print op, fd}' | sort | uniq -c | sort -rn | head -20
} > summary.txt 2>&1
cat summary.txt
chmod -R a+rX "$OUT"; chown -R "$USER_NAME" "$OUT" 2>/dev/null
echo "done. Output in $OUT"; ls -la "$OUT" | head -30
