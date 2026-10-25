#!/usr/bin/env python3
"""Does `fm serve` honor `max_tokens`, or only `max_completion_tokens`? One prompt, four settings, temperature 0, no streaming.
Starts `fm serve` on port 18990, sends the four requests, stops the server, and writes the answers' token counts to probe_max_tokens.jsonl.
Written 2026-10-24 after a September how-to (note 52 of the article) reported that `max_tokens` is ignored and `max_completion_tokens` works.
Run: python3 probe_max_tokens.py   (needs macOS 27 with `fm`; read the notice printed by `fm license --show` first)"""
import json
import subprocess
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
PORT = 18990
PROMPT = "Explain what a static site generator is."
srv = subprocess.Popen(["fm", "serve", "--port", str(PORT)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
rows = []
try:
    for _ in range(60):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2); break
        except Exception:
            time.sleep(1)

    def call(extra):
        body = {"model": "system", "stream": False, "temperature": 0, "messages": [{"role": "user", "content": PROMPT}]}
        body.update(extra)
        t = time.time()
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"}), timeout=120))
            ch = r["choices"][0]
            return {"params": extra, "completion_tokens": r["usage"]["completion_tokens"], "finish_reason": ch.get("finish_reason"), "chars": len(ch["message"]["content"]), "seconds": round(time.time() - t, 2)}
        except Exception as e:
            return {"params": extra, "error": str(e)[:200]}

    for extra in ({}, {"max_tokens": 5}, {"max_completion_tokens": 5}, {"max_completion_tokens": 20}):
        rows.append(call(extra)); print(json.dumps(rows[-1]), flush=True)
finally:
    srv.terminate()
    try: srv.wait(10)
    except Exception: srv.kill()
(HERE / "probe_max_tokens.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
