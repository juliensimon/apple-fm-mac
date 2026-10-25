#!/bin/bash
# A third reading of the expert reselection cadence, at a writing speed different from the two traced on 2026-10-24
# (58 tokens a second, code answer; 33 a second, essay answer). Added 2026-10-25 after the story meeting
# (desk/storymeeting-design-evans.md: "the fixed cadence in tokens is the real evidence, and it rests on two prompts").
#
# Run:   sudo bash inspect_ifp_cadence.sh     (run_followups.sh calls it)
# Takes: about 3 minutes. Writes to ./ifp_cadence_out/ next to this script.
# Records system-call names, file descriptors, offsets and sizes of reads on the main provider (fs_usage), never the
# contents of a read. No memory read, no debugger, no change to any setting. Same method as docs/apple-fm/data/inspect_ifp.sh.
#
# Hypothesis H5, written before any result: in the long-context prompt (about 3,000 tokens in, a long answer, so a slower
# writing speed than 58), the spacing of read bursts after the first, converted to tokens with that prompt's own writing
# speed, is 32 tokens give or take 4. Holds if the median spacing is 28 to 36 tokens; fails if it is outside 24 to 40.
# A fresh subject (geology) gives one more first-burst size.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/ifp_cadence_out"
USER_NAME="${SUDO_USER:-$(logname)}"
if [ "$(id -u)" -ne 0 ]; then echo "run with sudo"; exit 1; fi
if pgrep -f "mlx_lm.server --model" >/dev/null || pgrep -x powermetrics >/dev/null; then echo "STOP: another measurement is running"; exit 1; fi
mkdir -p "$OUT"; chown "$USER_NAME" "$OUT"; cd "$OUT" || exit 1
export NO_COLOR=1
as_user() { sudo -u "$USER_NAME" env NO_COLOR=1 "$@"; }
mark() { echo "$(python3 -c 'import time;print(f"{time.time():.3f}")') $*" >> phases.txt; }
as_user fm respond --no-stream -g -- 'Reply with the single word OK.' > /dev/null 2>&1
sleep 1
MAIN="$(ps -axo pid=,rss=,command= | grep 'TGOnDeviceInferenceProviderService.appex' | grep -v grep | sort -k2 -n -r | head -1 | awk '{print $1}')"
echo "main provider pid: $MAIN" | tee main_pid.txt
fs_usage -w -f filesys -f pager "$MAIN" > fs_cadence.txt 2>&1 &
FU=$!
sleep 1
run() { label="$1"; shift; mark "start_$label"; as_user fm respond --no-stream -g "$@" > "out_$label.txt" 2>&1 < /dev/null; mark "end_$label"; sleep 1.5; }
run geology  -- 'Explain how plate tectonics shapes mountain ranges, with three examples, in about 400 words.'
run longctx  -- "$(cat "$HERE/cadence_long_prompt.txt")"
kill "$FU" 2>/dev/null; wait "$FU" 2>/dev/null
chmod -R a+rX "$OUT"; chown -R "$USER_NAME" "$OUT" 2>/dev/null
echo "trace done: $OUT"
