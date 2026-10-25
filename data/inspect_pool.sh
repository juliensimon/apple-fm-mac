#!/bin/bash
# How long does the K and V pool stay allocated after a request?
#
# Run:   sudo bash inspect_pool.sh
# Takes: about 2 minutes. Writes to ./pool_out/ next to this script.
#
# Sends one 4,900-token prompt (the 8,192-token bucket, a 560 MiB K and V pair), then samples `vmmap -summary` of
# the main inference provider once per second for 90 seconds and records the IOSurface size. The time at which it
# falls back to the 245 MiB baseline is the pool lifetime. No memory contents are read.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; OUT="$HERE/pool_out"
USER_NAME="${SUDO_USER:-$(logname)}"
if [ "$(id -u)" -ne 0 ]; then echo "run with sudo"; exit 1; fi
mkdir -p "$OUT"; chown "$USER_NAME" "$OUT"; cd "$OUT" || exit 1
export NO_COLOR=1
as_user() { sudo -u "$USER_NAME" env NO_COLOR=1 "$@"; }
as_user fm respond --no-stream -g -- 'Reply with the single word OK.' > /dev/null 2>&1; sleep 5
MAIN="$(ps -axo pid=,rss=,command= | grep 'TGOnDeviceInferenceProviderService.appex' | grep -v grep | sort -k2 -n -r | head -1 | awk '{print $1}')"
echo "main provider pid: $MAIN"
FILLER="The quick brown fox jumps over the lazy dog near the quiet river. "
python3 -c "open('p.txt','w').write(('$FILLER' * 340) + '\nReply with the single word DONE.')"; chown "$USER_NAME" p.txt
printf 'epoch_s\tseconds_since_request_end\tiosurface_resident\tphase\n' > pool.tsv
T0=$(python3 -c 'import time;print(time.time())')
as_user fm respond --no-stream -g -- "$(cat p.txt)" > /dev/null 2>&1 &
BG=$!
END=""
for i in $(seq 1 120); do
  NOW=$(python3 -c 'import time;print(time.time())')
  if [ -z "$END" ] && ! kill -0 "$BG" 2>/dev/null; then END="$NOW"; fi
  vmmap -summary "$MAIN" 2>/dev/null | grep -a '^IOSurface' | head -1 | awk -v now="$NOW" -v end="$END" -v t0="$T0" '{ph=(end==""?"running":"after"); since=(end==""?now-t0:now-end); printf "%s\t%.1f\t%s\t%s\n", now, since, $3, ph}' >> pool.tsv
  [ -n "$END" ] && [ "$(python3 -c "print(1 if $NOW-$END>90 else 0)")" = "1" ] && break
  sleep 0.5
done
cat pool.tsv | awk 'NR==1 || NR%4==2' | head -80
chmod -R a+rX "$OUT"; chown -R "$USER_NAME" "$OUT" 2>/dev/null
echo "done. Output in $OUT"
