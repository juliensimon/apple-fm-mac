#!/usr/bin/env python3
"""Sample GPU utilization, GPU memory and provider CPU time while fm runs prefill-heavy and decode-heavy work.
Run: bash data/make_square_images.sh (once, for data/img/i1024.png), then python3 data/hw.py   (writes data/hw.json)"""
import json, os, re, subprocess, threading, time

ENV = dict(os.environ, NO_COLOR="1", TERM="dumb")
HERE = os.path.dirname(os.path.abspath(__file__))
samples = []
phase = ["idle"]
stop = False


def gpu():
    out = subprocess.run(["ioreg", "-r", "-c", "AGXAccelerator", "-w0"], capture_output=True, text=True).stdout
    m = re.search(r'"Device Utilization %"=(\d+)', out)
    r = re.search(r'"Renderer Utilization %"=(\d+)', out)
    mem = re.search(r'"In use system memory"=(\d+)', out)
    return (int(m.group(1)) if m else None, int(r.group(1)) if r else None, int(mem.group(1)) if mem else None)


def provider():
    out = subprocess.run(["ps", "-axo", "pid=,cputime=,rss=,command="], capture_output=True, text=True).stdout
    res = {}
    for l in out.splitlines():
        if "TGOnDeviceInferenceProviderService" in l and ".appex" in l:
            p = l.split(None, 3)
            t = p[1]
            parts = t.split(":")
            secs = float(parts[-1]) + 60 * int(parts[-2]) + (3600 * int(parts[-3]) if len(parts) > 2 else 0)
            res[int(p[0])] = (secs, int(p[2]))
    return res


def sampler():
    t0 = time.perf_counter()
    while not stop:
        g = gpu()
        samples.append({"t": time.perf_counter() - t0, "phase": phase[0], "gpu": g[0], "render": g[1], "gpu_mem": g[2], "prov": provider()})
        time.sleep(0.05)


th = threading.Thread(target=sampler)
th.start()


def run(label, cmd):
    phase[0] = label
    t0 = time.perf_counter()
    subprocess.run(cmd, capture_output=True, text=True, env=ENV, stdin=subprocess.DEVNULL, timeout=300)
    return time.perf_counter() - t0


time.sleep(2)
filler = "The quick brown fox jumps over the lazy dog near the quiet river. "
long_prompt = filler * 420 + "\nReply with the single word DONE."
res = {}
res["prefill_5k_s"] = run("prefill", ["fm", "respond", "--no-stream", "-g", "--", long_prompt])
phase[0] = "idle2"; time.sleep(2)
res["decode_s"] = run("decode", ["fm", "respond", "--no-stream", "-g", "--", "Write a 400 word story about a robot learning to paint."])
phase[0] = "idle3"; time.sleep(2)
res["image_s"] = run("image", ["fm", "respond", "--no-stream", "-g", "--image", os.path.join(HERE, "img/i1024.png"), "--text", "Describe this image in detail."])
phase[0] = "idle4"; time.sleep(2)
stop = True
th.join()

summary = {}
for ph in ("idle", "prefill", "decode", "image", "idle2", "idle3", "idle4"):
    rows = [s for s in samples if s["phase"] == ph]
    if not rows:
        continue
    gp = [r["gpu"] for r in rows if r["gpu"] is not None]
    mem = [r["gpu_mem"] for r in rows if r["gpu_mem"]]
    # provider cpu seconds consumed during the phase, summed over pids
    pids = set(k for r in rows for k in r["prov"])
    cpu = 0.0
    for pid in pids:
        v = [r["prov"][pid][0] for r in rows if pid in r["prov"]]
        cpu += max(v) - min(v)
    dur = rows[-1]["t"] - rows[0]["t"]
    summary[ph] = {"n": len(rows), "seconds": round(dur, 2), "gpu_mean": round(sum(gp) / len(gp), 1), "gpu_max": max(gp),
                   "gpu_mem_max_mb": round(max(mem) / 1e6) if mem else None, "provider_cpu_s": round(cpu, 2),
                   "provider_cpu_pct_of_one_core": round(100 * cpu / dur, 1) if dur else None}
res["summary"] = summary
json.dump({"res": res, "samples": samples}, open(os.path.join(HERE, "hw.json"), "w"))
print(json.dumps(res, indent=1))
