# Parameter probes against Apple's `fm serve` (REPORT 7.2): one prompt per parameter, then sampling, system role, structured output, tools.
# Run: fm serve --host 127.0.0.1 --port 18976   (in another terminal), then: python3 data/api2.py
import json, time, urllib.request
A = "http://127.0.0.1:18976/v1/chat/completions"
def call(msgs, **kw):
    body = {"model": "system", "messages": msgs, "stream": False}; body.update(kw)
    req = urllib.request.Request(A, json.dumps(body).encode(), {"Content-Type": "application/json"})
    t = time.perf_counter()
    try:
        r = json.load(urllib.request.urlopen(req, timeout=120)); return round(time.perf_counter() - t, 2), r
    except urllib.error.HTTPError as e:
        return round(time.perf_counter() - t, 2), {"HTTP": e.code, "body": e.read().decode()[:400]}
def show(label, r):
    if "choices" in r:
        c = r["choices"][0]; print(f"{label}: finish={c.get('finish_reason')} usage={r['usage']['prompt_tokens']}/{r['usage']['completion_tokens']} msg={json.dumps(c['message'])[:300]}")
    else: print(f"{label}: {r}")
u = lambda s: [{"role": "user", "content": s}]
for label, kw in [("max_tokens=5", dict(max_tokens=5)), ("temperature=0", dict(temperature=0)), ("temperature=2", dict(temperature=2)),
                  ("top_p=0.1", dict(top_p=0.1)), ("seed=1", dict(seed=1)), ("stop=['.']", dict(stop=["."])), ("n=2", dict(n=2)),
                  ("logprobs", dict(logprobs=True, top_logprobs=3)), ("presence_penalty", dict(presence_penalty=1.0)),
                  ("frequency_penalty", dict(frequency_penalty=1.0)), ("unknown param", dict(banana=1))]:
    dt, r = call(u("Write one sentence about the sea."), **kw); print(dt, end=" "); show(label, r)
print("== temperature spread (5 runs each, same prompt)")
for T in (0, 1, 2):
    outs = [call(u("Name a color."), temperature=T)[1]["choices"][0]["message"]["content"] for _ in range(5)]
    print("T", T, sorted(set(outs)), len(set(outs)))
print("== system role")
dt, r = call([{"role": "system", "content": "Answer only in French."}, {"role": "user", "content": "How are you?"}]); show("system msg", r)
print("== response_format json_schema")
rf = {"type": "json_schema", "json_schema": {"name": "P", "schema": {"type": "object", "properties": {"name": {"type": "string"}, "age": {"type": "integer"}}, "required": ["name", "age"], "additionalProperties": False}, "strict": True}}
dt, r = call(u("Marie is 22."), response_format=rf); show("json_schema", r)
dt, r = call(u("Give me JSON with a key city."), response_format={"type": "json_object"}); show("json_object", r)
print("== tools")
tools = [{"type": "function", "function": {"name": "get_weather", "description": "Get current weather for a city", "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}}]
dt, r = call(u("What's the weather in Paris?"), tools=tools); print(dt, end=" "); show("tools", r)
dt, r = call(u("What's the weather in Paris?"), tools=tools, tool_choice="required"); print(dt, end=" "); show("tool_choice=required", r)
dt, r = call(u("Tell me a joke."), tools=tools); print(dt, end=" "); show("tools unused", r)
msgs = u("What's the weather in Paris?")
dt, r = call(msgs, tools=tools)
tc = r.get("choices", [{}])[0].get("message", {}).get("tool_calls")
if tc:
    msgs += [r["choices"][0]["message"], {"role": "tool", "tool_call_id": tc[0]["id"], "content": "{\"temp_c\": 17, \"sky\": \"cloudy\"}"}]
    dt, r2 = call(msgs, tools=tools); print(dt, end=" "); show("tool result -> answer", r2)
