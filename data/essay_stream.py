"""Stream the five-topic essay of the expert-loading trace again, with timestamps, to map trace time to text position (REPORT 21.5).
Run: python3 data/essay_stream.py   (writes data/essay_stream.json; compares the text with the traced run in data/ifp_trace_2026-10-24/)"""
import json, os, subprocess, time
HERE = os.path.dirname(os.path.abspath(__file__))
ENV = dict(os.environ, NO_COLOR="1", TERM="dumb")
P = 'Write a very long essay, at least 1500 words, that moves through these five topics in this order: black holes, sourdough baking, contract law, the history of jazz, and marine biology. Do not stop early and do not summarize.'
t0 = time.perf_counter()
p = subprocess.Popen(["fm", "respond", "--stream", "-g", "--", P], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV, stdin=subprocess.DEVNULL)
chunks = []; buf = b""
while True:
    b = p.stdout.read1(65536)
    if not b: break
    buf += b; chunks.append((time.perf_counter() - t0, len(buf.decode(errors="ignore"))))
p.wait()
text = buf.decode(errors="replace")
json.dump({"chunks": chunks, "text": text}, open(os.path.join(HERE, "essay_stream.json"), "w"))
ref = open(os.path.join(HERE, "ifp_trace_2026-10-24", "out_essay.txt")).read()
print("chunks", len(chunks), "chars", len(text), "total s", round(chunks[-1][0], 1), "identical to the traced run:", text.strip() == ref.strip())
