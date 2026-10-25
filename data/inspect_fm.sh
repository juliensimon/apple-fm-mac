#!/bin/bash
# Root observation of the Apple Foundation Models runtime on this Mac.
#
# Run:   sudo bash inspect_fm.sh
# Takes: about 90 seconds. Writes to ./fm_root_out/ next to this script, then makes it readable.
#
# What it does:
#   1. Snapshots the model processes before any load: open files (lsof), memory regions (vmmap -summary),
#      physical footprint (footprint), and system memory (vm_stat, swap).
#   2. Runs powermetrics for ANE, GPU and CPU power while a fixed workload runs as the normal user:
#      idle, a 5,000 token prefill, a long decode, an image request, idle.
#   3. Logs page-ins and file reads by the provider processes during the decode (fs_usage).
#   4. Snapshots the same things again right after the workload.
#
# What it does not do: no stack sampling, no memory dumps, no debugger attach, no change to SIP or any setting.
# Everything is read-only observation. The only writes are the files in fm_root_out/.

set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/fm_root_out"
USER_NAME="${SUDO_USER:-$(logname)}"
mkdir -p "$OUT"
chown "$USER_NAME" "$OUT" 2>/dev/null   # the normal user must be able to write the test image here
cd "$OUT" || exit 1
export NO_COLOR=1

if [ "$(id -u)" -ne 0 ]; then echo "run with sudo"; exit 1; fi

as_user() { sudo -u "$USER_NAME" env NO_COLOR=1 "$@"; }
mark() { echo "$(date +%s.%N) $*" >> phases.txt; }

provider_pids() { pgrep -f 'TGOnDeviceInferenceProviderService.appex' | tr '\n' ' '; }
service_pids() { pgrep -f 'modelmanagerd|modelcatalogd|/aned|GenerativeExperiencesSafetyInferenceProvider|ANECompilerService' | tr '\n' ' '; }

snapshot() {
  tag="$1"
  {
    date
    echo "## sysctl"; sysctl hw.memsize hw.pagesize vm.swapusage 2>&1
    echo "## vm_stat"; vm_stat
    echo "## memory_pressure"; memory_pressure 2>&1 | tail -8
    for pid in $(provider_pids) $(service_pids); do
      echo; echo "################ pid $pid: $(ps -o user=,rss=,vsz=,thcount=,etime=,command= -p "$pid" | cut -c1-170)"
      echo "--- footprint"; footprint "$pid" 2>&1 | head -30
      echo "--- vmmap -summary"; vmmap -summary "$pid" 2>&1 | head -70
      echo "--- lsof: types"; lsof -p "$pid" -n -P 2>/dev/null | awk 'NR>1{print $5}' | sort | uniq -c | sort -rn
      echo "--- lsof: regular files, devices, and mach/iokit"; lsof -p "$pid" -n -P 2>/dev/null | awk 'NR==1 || $5=="REG" || $5=="CHR" || $5=="DIR"' | cut -c1-230
    done
  } > "snapshot_$tag.txt" 2>&1
}

echo "[1/5] idle snapshot"; mark snapshot_before; snapshot before

# Warm the model so the providers are loaded, then take the loaded snapshot.
as_user fm respond --no-stream -g -- 'Reply with the single word OK.' > /dev/null 2>&1
sleep 1

echo "[2/5] powermetrics + workload"
# 250 ms samples, 160 samples = 40 s.
powermetrics --samplers cpu_power,gpu_power,ane_power -i 250 -n 160 > powermetrics.txt 2>&1 &
PM=$!
sleep 2.5; mark idle_start; sleep 2; mark idle_end

PIDS="$(provider_pids)"
# fs_usage on the provider processes: page-ins and file reads only.
# shellcheck disable=SC2086
fs_usage -w -f pager -f filesys $PIDS > fs_usage.txt 2>&1 &
FU=$!

python3 - <<'PY' > /dev/null 2>&1
open("long_prompt.txt","w").write(("The quick brown fox jumps over the lazy dog near the quiet river. " * 350) + "\nReply with the single word DONE.")
PY
chown "$USER_NAME" long_prompt.txt 2>/dev/null

mark prefill_start; as_user fm respond --no-stream -g -- "$(cat long_prompt.txt)" > /dev/null 2>&1; mark prefill_end
sleep 2
mark decode_start; as_user fm respond --no-stream -g -- 'Write a 400 word story about a robot learning to paint.' > /dev/null 2>&1; mark decode_end
sleep 2
IMG="$(ls /System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/Accounts.icns 2>/dev/null)"
if [ -n "$IMG" ]; then
  as_user sips -s format png "$IMG" --out "$OUT/img.png" > /dev/null 2>&1
  mark image_start; as_user fm respond --no-stream -g --image "$OUT/img.png" --text 'Describe this image in detail.' > /dev/null 2>&1; mark image_end
fi
sleep 2
mark final_idle_start; sleep 4; mark final_idle_end

kill "$FU" 2>/dev/null; wait "$FU" 2>/dev/null
wait "$PM" 2>/dev/null

echo "[3/5] loaded snapshot"; mark snapshot_after; snapshot after

echo "[4/5] services"
{
  echo "## ioreg ANE"; ioreg -rc H11ANEIn -w0 2>&1 | head -40
  echo "## ioreg GPU stats"; ioreg -r -c AGXAccelerator -w0 2>&1 | grep -a PerformanceStatistics | head -2
  echo "## launchctl: model services"; launchctl print system 2>&1 | grep -Ei 'modelmanager|modelcatalog|aned|tgon|generativeexp' | head -20
  echo "## provider entitlements (names only)"
  for p in /System/Library/ExtensionKit/Extensions/TGOnDeviceInferenceProviderService.appex /usr/libexec/modelmanagerd; do
    echo "-- $p"; codesign -d --entitlements - "$p" 2>&1 | grep -aE 'com\.apple\.[a-zA-Z0-9._-]+' | sed -E 's/^[[:space:]]*//' | head -40
  done
} > services.txt 2>&1

echo "[5/5] summarising powermetrics"
python3 - <<'PY' > powermetrics_summary.txt 2>&1
import re, statistics
txt = open("powermetrics.txt", errors="ignore").read()
blocks = txt.split("*** Sampled system activity")[1:]
rows = []
for b in blocks:
    def g(pat):
        m = re.search(pat, b)
        return float(m.group(1)) if m else None
    ts = re.search(r"\(([^)]*)\)", b)
    rows.append({"ts": ts.group(1) if ts else "", "ane_mw": g(r"ANE Power:\s*([\d.]+)\s*mW"), "gpu_mw": g(r"GPU Power:\s*([\d.]+)\s*mW"),
                 "cpu_mw": g(r"CPU Power:\s*([\d.]+)\s*mW"), "gpu_freq": g(r"GPU HW active frequency:\s*([\d.]+)\s*MHz"),
                 "gpu_res": g(r"GPU HW active residency:\s*([\d.]+)%"), "combined_mw": g(r"Combined Power \(CPU \+ GPU \+ ANE\):\s*([\d.]+)\s*mW")})
print("samples:", len(rows))
def st(k):
    v = [r[k] for r in rows if r[k] is not None]
    return (round(min(v), 1), round(statistics.mean(v), 1), round(max(v), 1)) if v else None
for k in ("ane_mw", "gpu_mw", "cpu_mw", "combined_mw", "gpu_freq", "gpu_res"):
    print(k, "min/mean/max", st(k))
print()
print("per-sample table (timestamp, ANE mW, GPU mW, CPU mW):")
for r in rows:
    print(r["ts"], r["ane_mw"], r["gpu_mw"], r["cpu_mw"])
PY

chmod -R a+rX "$OUT"
chown -R "$USER_NAME" "$OUT" 2>/dev/null
echo "done. Output in $OUT"
ls -la "$OUT"
