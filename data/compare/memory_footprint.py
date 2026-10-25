#!/usr/bin/env python3
"""Memory of one open build behind a local server, by the same macOS tool (`footprint`) that gave the figures for Apple's model
(REPORT 12 and 28.1). One reply of at most 300 tokens (64 to 195 came back) to a fixed math prompt, then footprint of the server process; a second reading ten seconds later.
Written 2026-10-24 so that both sides are measured with the same instrument (the first memory run, memory_open_models.py, used MLX's own
counters; Apple's figure comes from footprint and vmmap).
Run: uv run --quiet --no-project --with mlx-lm python data/compare/memory_footprint.py <hf repo> <label> <port>   (appends to memory_footprint.json)
"""
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
repo, label, port = sys.argv[1], sys.argv[2], int(sys.argv[3])
PROMPT = ("Solve the following math problem step by step. At the end, write the final number on its own line as 'Answer: <number>'.\n\n"
          "A robe takes 2 bolts of blue fiber and half that much white fiber. How many bolts in total does it take?")


def footprint(pid):
    out = subprocess.run(["footprint", str(pid)], capture_output=True, text=True).stdout
    m = re.search(r"Footprint:\s*([\d.]+)\s*(KB|MB|GB)", out)
    if not m:
        return None
    v = float(m.group(1))
    return round(v / 1024 if m.group(2) == "KB" else v if m.group(2) == "MB" else v * 1024, 1)


srv = subprocess.Popen(["uv", "run", "--quiet", "--no-project", "--with", "mlx-lm", "mlx_lm.server", "--model", repo, "--port", str(port), "--temp", "0.0",
                        "--chat-template-args", json.dumps({"enable_thinking": False})], stdout=open(HERE / f"server_mem_{label}.log", "w"), stderr=subprocess.STDOUT)
try:
    for _ in range(300):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=2); break
        except Exception:
            time.sleep(2)
    pid = int(subprocess.run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"], capture_output=True, text=True).stdout.split()[0])
    before = footprint(pid)
    body = json.dumps({"model": repo, "messages": [{"role": "user", "content": PROMPT}], "stream": False, "temperature": 0, "max_tokens": 300}).encode()
    r = json.load(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", body, {"Content-Type": "application/json"}), timeout=1800))
    after = footprint(pid)
    time.sleep(10)
    idle = footprint(pid)
    row = {"repo": repo, "label": label, "date": time.strftime("%Y-%m-%d"), "footprint_mib_before_request": before, "footprint_mib_after_request": after,
           "footprint_mib_ten_seconds_later": idle, "reply_tokens": r.get("usage", {}).get("completion_tokens")}
    path = HERE / "memory_footprint.json"
    rows = json.load(open(path)) if path.exists() else []
    rows.append(row)
    json.dump(rows, open(path, "w"), indent=1)
    print(row, flush=True)
finally:
    srv.terminate()
    try: srv.wait(30)
    except Exception: srv.kill()
