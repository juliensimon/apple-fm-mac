#!/usr/bin/env python3
"""The dated-event questions through Core Advanced on `fm serve` (documented HTTP server), temperature 0, same prompt and scorer as compare_models.py.
Needs `fm serve --host 127.0.0.1 --port 18976` running. Writes results_apple.json (dated section only)."""
import json, re, time, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
URL = "http://127.0.0.1:18976/v1/chat/completions"
ABSTAIN = re.compile(r"don't know|do not know|not aware|no information|cannot|can't|as of my|knowledge cutoff|unable|unsure|no record|haven't|not sure|don't have", re.I)


def ask(prompt):
    body = json.dumps({"model": "system", "messages": [{"role": "user", "content": prompt}], "stream": False, "temperature": 0}).encode()
    try:
        return json.load(urllib.request.urlopen(urllib.request.Request(URL, body, {"Content-Type": "application/json"}), timeout=120))["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        return f"[HTTP {e.code}]"


MODES = {"abstain": "Answer in one short sentence. If you do not know, reply 'I do not know'.", "guess": "Answer in one short sentence."}
out = {"repo": "Core Advanced via fm serve (macOS 27.0.1, 26A434)", "slug": "apple", "date": time.strftime("%Y-%m-%d")}
for mode, lead in MODES.items():
    rows = []
    for e in json.load(open(HERE / "dated_events.json")):
        text = ask(f"{lead}\n\n{e['q']}")
        status = "correct" if re.search(e["gold"], text, re.I) else ("abstain" if ABSTAIN.search(text) else "wrong")
        rows.append({**e, "answer": text.strip()[:160], "status": status})
    out["dated_" + mode] = {"rows": rows}
    for grp in ["anchor", "before Sep 2024", "Sep 2024 to Jan 2025", "Feb 2025 to Jun 2025"]:
        rs = [r for r in rows if r["group"] == grp]
        print(f"{mode:8s} {grp:22s} correct {sum(r['status'] == 'correct' for r in rs)}/{len(rs)}  wrong {sum(r['status'] == 'wrong' for r in rs)}  abstain {sum(r['status'] == 'abstain' for r in rs)}")
json.dump(out, open(HERE / "results_apple.json", "w"), indent=1, ensure_ascii=False)
