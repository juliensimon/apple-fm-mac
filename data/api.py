# Caching tests against Apple's `fm serve` (REPORT 7.3): the same prompt four times, a shared prefix with three tails, a growing chat.
# Run: fm serve --host 127.0.0.1 --port 18976   (in another terminal), then: python3 data/api.py
import json, time, urllib.request
A = "http://127.0.0.1:18976/v1/chat/completions"
def call(msgs, **kw):
    body = {"model": "system", "messages": msgs, "stream": False}; body.update(kw)
    req = urllib.request.Request(A, json.dumps(body).encode(), {"Content-Type": "application/json"})
    t = time.perf_counter()
    try:
        r = json.load(urllib.request.urlopen(req, timeout=120)); dt = time.perf_counter() - t
        return dt, r
    except urllib.error.HTTPError as e:
        return time.perf_counter() - t, {"HTTP": e.code, "body": e.read().decode()[:300]}
filler = "The quick brown fox jumps over the lazy dog near the quiet river. "
long = filler * 140
q = [{"role": "user", "content": long + "\nReply with the single word DONE."}]
print("== prefix caching, same prompt x4")
for i in range(4):
    dt, r = call(q, temperature=0)
    u = r.get("usage", r); print(i, round(dt, 2), u.get("prompt_tokens"), u.get("prompt_tokens_details"), r.get("choices", [{}])[0].get("message", {}).get("content"))
print("== shared prefix, different tail")
for tail in ("Reply with the word ALPHA.", "Reply with the word BETA.", "Reply with the word GAMMA."):
    dt, r = call([{"role": "user", "content": long + "\n" + tail}], temperature=0)
    u = r.get("usage", r); print(tail[-6:], round(dt, 2), u.get("prompt_tokens"), u.get("prompt_tokens_details"))
print("== multi-turn growth")
msgs = [{"role": "user", "content": long + "\nRemember the code word: PELICAN. Reply OK."}]
for i in range(3):
    dt, r = call(msgs, temperature=0); a = r["choices"][0]["message"]["content"]; u = r["usage"]
    print("turn", i, round(dt, 2), u["prompt_tokens"], u["prompt_tokens_details"], repr(a[:40]))
    msgs += [{"role": "assistant", "content": a}, {"role": "user", "content": "What is the code word? One word."}]
