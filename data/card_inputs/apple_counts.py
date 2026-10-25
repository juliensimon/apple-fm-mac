# Apple's token count for each of the 429 strings: `fm count-tokens -q`, minus the one token it adds to any text (REPORT 27.1).
# As run on 2026-10-24. It reads corpus.json, which is not in this repository (170 of its strings are private).
# To run the same test on any strings: scripts/tokenizer_test.py.
import json, os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
ENV = dict(os.environ, NO_COLOR="1", TERM="dumb")
cats = json.load(open(os.path.join(HERE, "corpus.json"))); out = {}
for cat, items in cats.items():
    out[cat] = []
    for s in items:
        r = subprocess.run(["fm", "count-tokens", "-q", "--", s], capture_output=True, text=True, env=ENV, stdin=subprocess.DEVNULL, timeout=60)
        try: out[cat].append(int(r.stdout.strip()) - 1)
        except ValueError: out[cat].append(None)
json.dump(out, open(os.path.join(HERE, "apple_counts.json"), "w"))
print({k: (len(v), sum(x is None for x in v)) for k, v in out.items()})
