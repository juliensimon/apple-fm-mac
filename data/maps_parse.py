"""Parse the `vmmap -v -interleaved` region lists saved by data/inspect_maps.sh and print totals by region type.
Run inside the output folder: cd data/maps_out && python3 ../maps_parse.py <pid> <process name>
The saved maps of 2026-10-24 are not in this repository (they list file paths inside Apple's protected asset folder);
the tables derived from them are data/plots/memory_by_region_type.csv, iosurface_regions.csv and neural_and_gpu_regions.csv."""
import re, sys, collections
def size(s):
    m = re.match(r"([\d.]+)([KMG]?)", s.strip())
    v = float(m.group(1)); return int(v * {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3}[m.group(2)])
RX = re.compile(r"^(?P<type>.+?)\s+(?P<s>[0-9a-f]+)-(?P<e>[0-9a-f]+)\s+\[\s*(?P<v>\S+)\s+(?P<r>\S+)\s+(?P<d>\S+)\s+(?P<w>\S+)\]\s+(?P<prot>\S+)\s+SM=(?P<sm>\S+)\s*(?:PURGE=\S+)?\s*(?P<detail>.*)$")
def load(path):
    out = []; inreg = False
    for l in open(path, errors="ignore"):
        if l.startswith("==== regions"): inreg = True; continue
        if l.startswith("==== Legend"): break
        if not inreg: continue
        m = RX.match(l.rstrip("\n"))
        if m:
            d = m.groupdict(); d["s"] = int(d["s"], 16); d["e"] = int(d["e"], 16)
            for k in "vrdw": d[k] = size(d[k])
            out.append(d)
    return out
if __name__ == "__main__":
    pid, name = sys.argv[1], sys.argv[2]
    snaps = {t: load(f"{t}_{name}_{pid}.vmmap_regions.txt") for t in ("idle", "during", "after")}
    for t, r in snaps.items():
        print(t, "regions", len(r), "virtual %.1f GB" % (sum(x["v"] for x in r)/2**30), "resident %.0f MB" % (sum(x["r"] for x in r)/2**20), "dirty %.0f MB" % (sum(x["d"] for x in r)/2**20))
    print()
    def agg(r):
        a = collections.defaultdict(lambda: [0, 0, 0, 0])
        for x in r:
            k = x["type"].strip(); a[k][0] += 1; a[k][1] += x["v"]; a[k][2] += x["r"]; a[k][3] += x["d"]
        return a
    A = {t: agg(r) for t, r in snaps.items()}
    types = sorted(set().union(*[a.keys() for a in A.values()]), key=lambda k: -A["idle"].get(k, [0, 0, 0, 0])[1])
    print("%-26s %7s %9s %9s | %9s %9s | %9s %9s" % ("type", "regions", "virt MB", "res MB", "res during", "dirty dur", "res after", "dirty aft"))
    for k in types[:30]:
        i = A["idle"].get(k, [0, 0, 0, 0]); d = A["during"].get(k, [0, 0, 0, 0]); a = A["after"].get(k, [0, 0, 0, 0])
        print("%-26s %7d %9.1f %9.1f | %9.1f %9.1f | %9.1f %9.1f" % (k[:26], i[0], i[1]/2**20, i[2]/2**20, d[2]/2**20, d[3]/2**20, a[2]/2**20, a[3]/2**20))
