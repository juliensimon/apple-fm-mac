#!/usr/bin/env python3
"""Does a fixed seed repeat the text? Four runs each through `fm serve`, default settings and temperature 1; appends two rows to template_probe.json.
Run after template_probe.py, with fm serve on port 18976: python3 data/card_inputs/seed_repeat.py"""
import json, os, urllib.request

os.chdir(os.path.dirname(os.path.abspath(__file__)))   # template_probe.json is beside this script

URL = "http://127.0.0.1:18976/v1/chat/completions"
PROMPT = [{"role": "user", "content": "Write one sentence of a story about a cat."}]


def call(**kw):
    body = json.dumps({"model": "system", "messages": PROMPT, "stream": False, **kw}).encode()
    return json.load(urllib.request.urlopen(urllib.request.Request(URL, body, {"Content-Type": "application/json"}), timeout=60))["choices"][0]["message"]["content"]


d = json.load(open("template_probe.json"))
d["sampling"] = [s for s in d["sampling"] if "seed 3" not in s["setting"]]
for label, kw in (("temperature 1, seed 3 repeated", {"temperature": 1.0, "seed": 3}), ("default, seed 3 repeated", {"seed": 3})):
    outs = [call(**kw) for _ in range(4)]
    d["sampling"].append({"setting": label, "runs": 4, "distinct": len(set(outs)), "samples": outs[:1]})
    print(label, "distinct:", len(set(outs)))
json.dump(d, open("template_probe.json", "w"), indent=1, ensure_ascii=False)
