#!/bin/bash
# Save the full memory-map METADATA of the Apple Foundation Models processes, for local analysis.
#
# Run:   sudo bash inspect_maps.sh
# Takes: about 60 seconds. Writes to ./maps_out/ next to this script.
#
# What is saved, per process and per snapshot:
#   vmmap -v -interleaved   every virtual memory region in address order: start, end, size, resident,
#                           dirty, swapped, permissions, region type, and the backing file path
#   vmmap -summary          totals per region type
#   footprint               physical footprint per category, including the "neural" owned memory
#   lsof -p                 every open file descriptor
# Snapshots: idle (model loaded), during (about 3 seconds into a 5,000-token prefill), after (generation finished).
#
# What it does NOT save: the contents of any memory. No process memory is read or copied.
# This is the layout (addresses, sizes, counters, file names), not the data. No debugger, no sampling, no SIP change.

set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/maps_out"
USER_NAME="${SUDO_USER:-$(logname)}"
if [ "$(id -u)" -ne 0 ]; then echo "run with sudo"; exit 1; fi
mkdir -p "$OUT"
chown "$USER_NAME" "$OUT"
cd "$OUT" || exit 1
export NO_COLOR=1
as_user() { sudo -u "$USER_NAME" env NO_COLOR=1 "$@"; }

PIDS="$(pgrep -f 'TGOnDeviceInferenceProviderService.appex' | tr '\n' ' ') $(pgrep -f 'GenerativeExperiencesSafetyInferenceProvider.appex' | tr '\n' ' ') $(pgrep -x modelmanagerd) $(pgrep -x aned) $(pgrep -x modelcatalogd)"
echo "pids: $PIDS" | tee pids.txt
for pid in $PIDS; do ps -o pid=,user=,rss=,etime=,command= -p "$pid" | cut -c1-200 >> pids.txt; done

snap() {
  tag="$1"
  for pid in $PIDS; do
    name="$(ps -o comm= -p "$pid" | xargs basename)"
    base="${tag}_${name}_${pid}"
    date +%s.%N > "${base}.time.txt"
    vmmap -v -interleaved "$pid" > "${base}.vmmap_regions.txt" 2>&1
    vmmap -summary "$pid" > "${base}.vmmap_summary.txt" 2>&1
    footprint "$pid" > "${base}.footprint.txt" 2>&1
    lsof -p "$pid" -n -P > "${base}.lsof.txt" 2>&1
  done
}

echo "[1/4] warm the model"
as_user fm respond --no-stream -g -- 'Reply with the single word OK.' > /dev/null 2>&1
sleep 1

echo "[2/4] snapshot: idle"
snap idle

echo "[3/4] snapshot: during a 5,000-token prefill"
python3 -c "open('long_prompt.txt','w').write(('The quick brown fox jumps over the lazy dog near the quiet river. ' * 350) + '\nReply with the single word DONE.')"
chown "$USER_NAME" long_prompt.txt
as_user fm respond --no-stream -g -- "$(cat long_prompt.txt)" > /dev/null 2>&1 &
BG=$!
sleep 3
snap during
wait "$BG" 2>/dev/null

echo "[4/4] snapshot: after"
sleep 2
snap after

chmod -R a+rX "$OUT"
chown -R "$USER_NAME" "$OUT" 2>/dev/null
echo "done. Output in $OUT"
ls -la "$OUT" | head -80
du -sh "$OUT"
