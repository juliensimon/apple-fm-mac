#!/bin/bash
# Energy per solved problem: CPU, GPU and Neural Engine power while each model solves the same 20 GSM8K problems.
#
# Run:   sudo bash run_energy.sh
# Takes: about 15 minutes. Needs the open builds already downloaded (see data/compare/run_server_checks.sh) and `fm serve` available.
#
# What it does: starts `powermetrics` (CPU, GPU and Neural Engine power, 500 ms samples) as root, runs energy_workload.py as the normal user
# (Apple's model through `fm serve`, then three 8-bit open builds through `mlx_lm.server`, same problems, same client), stops powermetrics,
# and runs energy_analyze.py. What it does not do: no stack sampling, no memory dumps, no debugger, no change to SIP or any setting.
# Everything is read-only observation; the only writes are powermetrics_energy.txt, phases.json, energy_results.json and energy_results.csv here.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
USER_NAME="${SUDO_USER:-$(logname)}"
cd "$HERE" || exit 1
if [ "$(id -u)" -ne 0 ]; then echo "run with sudo"; exit 1; fi
# do not start while another measurement or a model server runs: it would add its power to the baseline
if [ -f .measuring.lock ] && kill -0 "$(cat .measuring.lock)" 2>/dev/null; then echo "STOP: a measurement is running (.measuring.lock); wait for it to end, then run again"; exit 1; fi
if pgrep -f "mlx_lm.server --model" >/dev/null || pgrep -f "fm serve --port" >/dev/null; then echo "STOP: a model server is running; wait for it to end, then run again"; exit 1; fi
TAG="${ENERGY_TAG:-}"
rm -f "phases$TAG.json" "powermetrics_energy$TAG.txt"
chown "$USER_NAME" "$HERE" 2>/dev/null

# keep the Mac awake for the whole run: the 4-bit run of 2026-10-25 01:33 hit idle sleep twice (166 s and 284 s, pmset log)
caffeinate -dims -w $$ &
powermetrics --samplers cpu_power,gpu_power,ane_power -i 500 > "powermetrics_energy$TAG.txt" 2>&1 &
PM=$!
sleep 2
sudo -u "$USER_NAME" /bin/zsh -lc "cd '$HERE' && ENERGY_TAG='$TAG' NO_COLOR=1 uv run --quiet --no-project --with pandas --with pyarrow --with huggingface_hub python energy_workload.py 20"
WL=$?
sleep 2
kill -INT "$PM" 2>/dev/null; wait "$PM" 2>/dev/null
chown "$USER_NAME" "powermetrics_energy$TAG.txt" "phases$TAG.json" 2>/dev/null
if [ "$WL" -ne 0 ]; then echo "STOP: the workload failed (exit $WL); no analysis was run"; exit 1; fi
sudo -u "$USER_NAME" /bin/zsh -lc "cd '$HERE' && python3 energy_analyze.py powermetrics_energy$TAG.txt phases$TAG.json '$TAG'"
# a hole in the samples means the Mac slept or powermetrics stalled: the run is then not clean
python3 - "powermetrics_energy$TAG.txt" <<'PY'
import re, sys, datetime
ts = [datetime.datetime.strptime(" ".join(m.groups()), "%b %d %H:%M:%S %Y %z").timestamp()
      for m in re.finditer(r"\*{3} Sampled system activity \(\w+ (\w+ +\d+) (\d+:\d+:\d+) (\d+) ([+-]\d{4})\)", open(sys.argv[1], errors="ignore").read())]
gaps = [round(b - a, 1) for a, b in zip(ts, ts[1:]) if b - a > 2]
print("WARNING: holes in the power samples (s):", gaps, "- the Mac slept or stalled; rerun" if gaps else "") if gaps else print("samples continuous: no hole over 2 s")
PY
echo "done: energy_results$TAG.json, energy_results$TAG.csv"
