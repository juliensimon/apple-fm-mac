#!/bin/bash
# A read-only measurement to narrow the model's dimensions from sizes alone.
#
# Run:   sudo bash inspect_scale.sh
# Takes: two passes over ten prompt lengths, several minutes. Writes to ./scale_out/ next to this script.
#
# IOSurface memory against prompt length. For prompts of about 250 to 7,800 tokens, it samples
# `vmmap -summary` on the main inference provider while the prefill runs and keeps the peak.
# The slope (bytes per token) of the transient buffers is what a KV cache or activation buffer would show.
#
# No memory contents are read. No debugger, sampling, or setting is touched.
# The run of 2026-10-24 also had a part that listed the names and sizes of the model's asset files; it came back
# empty (the folder is protected, REPORT 18.9) and is left out of this copy.

set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/scale_out"
USER_NAME="${SUDO_USER:-$(logname)}"
if [ "$(id -u)" -ne 0 ]; then echo "run with sudo"; exit 1; fi
mkdir -p "$OUT"; chown "$USER_NAME" "$OUT"; cd "$OUT" || exit 1
export NO_COLOR=1
as_user() { sudo -u "$USER_NAME" env NO_COLOR=1 "$@"; }

echo "IOSurface against prompt length"
as_user fm respond --no-stream -g -- 'Reply with the single word OK.' > /dev/null 2>&1
sleep 1
# main provider = the TGOnDeviceInferenceProviderService with the larger RSS
MAIN="$(ps -axo pid=,rss=,command= | grep 'TGOnDeviceInferenceProviderService.appex' | grep -v grep | sort -k2 -n -r | head -1 | awk '{print $1}')"
echo "main provider pid: $MAIN" | tee main_pid.txt

FILLER="The quick brown fox jumps over the lazy dog near the quiet river. "
: > scale_summary.tsv
printf 'pass\treps\tprompt_tokens\twall_seconds\tpeak_iosurface_resident_mib\tpeak_iosurface_line\tvmmap_samples\n' >> scale_summary.tsv
for PASS in 1 2; do
for REPS in 17 35 70 140 210 280 350 420 480 540; do
  python3 -c "open('p_$REPS.txt','w').write(('$FILLER' * $REPS) + '\nReply with the single word DONE.')"
  chown "$USER_NAME" "p_$REPS.txt"
  TOK="$(as_user fm count-tokens -q -- "$(cat p_$REPS.txt)" </dev/null 2>/dev/null)"
  T0=$(python3 -c 'import time;print(time.time())')
  as_user fm respond --no-stream -g -- "$(cat p_$REPS.txt)" > /dev/null 2>&1 &
  BG=$!
  N=0; BEST=0; BESTLINE=""; NEURAL=""
  while kill -0 "$BG" 2>/dev/null; do
    vmmap -summary "$MAIN" > cur.txt 2>&1
    N=$((N+1))
    LINE="$(grep -a '^IOSurface' cur.txt | head -1)"
    # columns: IOSurface VIRTUAL RESIDENT DIRTY ... ; compare resident in MiB
    RES="$(echo "$LINE" | awk '{r=$3; u=substr(r,length(r)); v=substr(r,1,length(r)-1); if(u=="K")v=v/1024; if(u=="G")v=v*1024; print v}')"
    if [ -n "$RES" ] && [ "$(python3 -c "print(1 if float('${RES:-0}')>float('$BEST') else 0)")" = "1" ]; then BEST="$RES"; BESTLINE="$LINE"; cp cur.txt "peak_${REPS}_pass${PASS}.vmmap_summary.txt"; fi
  done
  T1=$(python3 -c 'import time;print(time.time())')
  SECS=$(python3 -c "print(round($T1-$T0,2))")
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$PASS" "$REPS" "$TOK" "$SECS" "$BEST" "$(echo "$BESTLINE" | tr -s ' ')" "$N" >> scale_summary.tsv
  echo "pass=$PASS reps=$REPS tokens=$TOK seconds=$SECS samples=$N peak_iosurface_resident_MiB=$BEST"
  sleep 2
done
done

chmod -R a+rX "$OUT"; chown -R "$USER_NAME" "$OUT" 2>/dev/null
echo "done. Output in $OUT"; ls -la "$OUT" | head -40
