#!/usr/bin/env python3
"""Memory of one open build behind a local server, taken the way Apple's model was (data/inspect_maps.sh): same moments, same long prompt.
Written 2026-10-24 after the hostile read of the Mac-first draft (desk/factcheck-7-mac-hostile.md) found three weaknesses in memory_footprint.py:
the 4-bit Qwen3 and Gemma 3 runs had the download and the model load inside the measured request, the reply length was a cap and not a length,
and Apple was read after a 5,000-token request while the open builds were read after a short one.
Steps, for one build:
  1. start `mlx_lm.server` with the build; wait until it answers;
  2. warm-up request (one short reply); sleep 1 s; `footprint` -> idle (Apple: one second after a one-word request);
  3. the long request: the same prompt as inspect_maps.sh (a 66-character sentence times 350, then "Reply with the single word DONE."), temperature 0,
     at most 8 tokens back; a thread runs `footprint` as fast as it can and keeps every reading: the reading nearest 3 s into the request is `during`
     (Apple: three seconds into the prefill) and the largest is `peak`;
  4. when the request ends: sleep 2 s -> after (Apple: two seconds after the request); sleep 10 s more -> ten_seconds_later.
Threshold written before any result: none; this run reports what it finds. The first readings (memory_footprint.json) stay in the repository.
Run: uv run --quiet --no-project --with mlx-lm python memory_protocol.py <hf repo> <label> <port>   (appends a row to memory_protocol.json)
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
repo, label, port = sys.argv[1], sys.argv[2], int(sys.argv[3])
LOCK = HERE / ".measuring.lock"
if subprocess.run(["pgrep", "-x", "powermetrics"], capture_output=True).returncode == 0:
    sys.exit("powermetrics is running (an energy run?): not starting")
LOCK.write_text(str(os.getpid()))
PROMPT = ("The quick brown fox jumps over the lazy dog near the quiet river. " * 350) + "\nReply with the single word DONE."


def footprint(pid):
    out = subprocess.run(["footprint", str(pid)], capture_output=True, text=True).stdout
    m = re.search(r"Footprint:\s*([\d.]+)\s*(KB|MB|GB)", out)
    if not m:
        return None
    v = float(m.group(1))
    return round(v / 1024 if m.group(2) == "KB" else v if m.group(2) == "MB" else v * 1024, 1)


def chat(content, max_tokens, timeout=1800):
    body = json.dumps({"model": repo, "messages": [{"role": "user", "content": content}], "stream": False, "temperature": 0, "max_tokens": max_tokens}).encode()
    return json.load(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", body, {"Content-Type": "application/json"}), timeout=timeout))


srv = subprocess.Popen(["uv", "run", "--quiet", "--no-project", "--with", "mlx-lm", "mlx_lm.server", "--model", repo, "--port", str(port), "--temp", "0.0",
                        "--chat-template-args", json.dumps({"enable_thinking": False})], stdout=open(HERE / f"server_proto_{label}.log", "w"), stderr=subprocess.STDOUT)
try:
    for _ in range(300):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=2); break
        except Exception:
            time.sleep(2)
    pid = int(subprocess.run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"], capture_output=True, text=True).stdout.split()[0])
    start_fp = footprint(pid)
    chat("Reply with the single word OK.", 8)                     # warm-up: loads the model if the server has not yet
    time.sleep(1)
    idle = footprint(pid)

    readings, stop = [], threading.Event()
    t0 = time.time()

    def poll():
        while not stop.is_set():
            v = footprint(pid)
            if v is not None:
                readings.append((round(time.time() - t0, 2), v))

    th = threading.Thread(target=poll, daemon=True); th.start()
    r = chat(PROMPT, 8)
    t_end = time.time() - t0
    stop.set(); th.join(timeout=30)
    time.sleep(2)
    after = footprint(pid)
    time.sleep(10)
    later = footprint(pid)
    near3 = min(readings, key=lambda x: abs(x[0] - 3.0)) if readings else None
    row = {"repo": repo, "label": label, "date": time.strftime("%Y-%m-%d"), "footprint_mib_server_started": start_fp, "footprint_mib_idle": idle,
           "footprint_mib_during_nearest_3s": near3[1] if near3 else None, "during_reading_at_s": near3[0] if near3 else None,
           "footprint_mib_peak": max(v for _, v in readings) if readings else None, "request_seconds": round(t_end, 2), "readings": len(readings),
           "footprint_mib_after_2s": after, "footprint_mib_ten_seconds_later": later,
           "prompt_tokens": r.get("usage", {}).get("prompt_tokens"), "reply_tokens": r.get("usage", {}).get("completion_tokens"),
           "reply": r["choices"][0]["message"]["content"][:40]}
    path = HERE / "memory_protocol.json"
    rows = json.load(open(path)) if path.exists() else []
    rows.append(row)
    json.dump(rows, open(path, "w"), indent=1)
    print(row, flush=True)
finally:
    srv.terminate()
    try: srv.wait(30)
    except Exception: srv.kill()
    try: LOCK.unlink()
    except Exception: pass
