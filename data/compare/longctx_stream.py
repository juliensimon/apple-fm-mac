"""Stream the traced long-context prompt again with timestamps, so the burst times of ifp_cadence_out/ can be turned into
token positions (same method as docs/apple-fm/data/essay_stream.py). No root; public `fm` command only. 2026-10-25."""
import json, os, subprocess, time
from pathlib import Path
H = Path(__file__).resolve().parent
ENV = dict(os.environ, NO_COLOR="1", TERM="dumb")
P = (H / "cadence_long_prompt.txt").read_text()
t0 = time.perf_counter()
p = subprocess.Popen(["fm", "respond", "--stream", "-g", "--", P], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV, stdin=subprocess.DEVNULL)
chunks = []; buf = b""
while True:
    b = p.stdout.read1(65536)
    if not b: break
    buf += b; chunks.append((time.perf_counter() - t0, len(buf.decode(errors="ignore"))))
p.wait()
text = buf.decode(errors="replace")
json.dump({"chunks": chunks, "text": text}, open(H / "ifp_cadence_out" / "longctx_stream.json", "w"))
ref = (H / "ifp_cadence_out" / "out_longctx.txt").read_text()
print("chunks", len(chunks), "chars", len(text), "first chunk s", round(chunks[0][0], 2), "total s", round(chunks[-1][0], 1), "identical to the traced run:", text.strip() == ref.strip())
