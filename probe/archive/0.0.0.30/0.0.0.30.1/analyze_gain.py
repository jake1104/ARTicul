"""0.0.0.30.1 part 1: planned-gain distribution on the CURRENT (V2) table."""
import re, os
import numpy as np

ROOT = r"E:\01_coding\ARTicul"
P = os.path.join(ROOT, "probe", "0.0.0.30.1")

items, cur = {}, None
for line in open(os.path.join(P, "plan.txt"), encoding="utf8"):
    line = line.rstrip("\n")
    m = re.match(r"== (.+?) :: (.*)", line)
    if m:
        cur = m.group(1)
        items[cur] = []
        continue
    m = re.match(r"u(\d+) sym=(.*?) dur=(\d+)ms stress=(\S+) word_final=(\S+) pause=(\S+) seglen=(\d+) arm=(\S+) base=(\S+) decl=(\S+) fin=(\S+) floor=(\d+) engine=(\S+)dB match=(\S+)", line)
    if m and cur is not None:
        items[cur]["append"] if False else items[cur].append({
            "i": int(m.group(1)), "sym": m.group(2), "dur": int(m.group(3)),
            "stress": m.group(4), "arm": m.group(8), "base": float(m.group(9)),
            "decl": float(m.group(10)), "fin": float(m.group(11)),
            "floor": int(m.group(12)), "g": float(m.group(13)),
            "match": m.group(14),
        })

nmm = sum(1 for segs in items.values() for s in segs if s["match"] != "OK")
print("engine-vs-probe match: %s (mismatches=%d)" % ("ALL OK" if nmm == 0 else "DIVERGED", nmm))

print("=== PER-ITEM PLANNED (V2 table) ===")
allg, floorn, neardb = [], 0, 0
for name, segs in items.items():
    gs = [s["g"] for s in segs]
    allg += gs
    floorn += sum(1 for s in segs if s["floor"])
    neardb += sum(1 for s in segs if s["g"] >= -1.0)
    steps = [abs(gs[k+1]-gs[k]) for k in range(len(gs)-1)]
    wi = int(np.argmax(steps)) if steps else -1
    print("%s n=%d min=%.2f max=%.2f spread=%.2f worst_step=%.2f(u%d->u%d) floor_n=%d declmax=%.1f fin_n=%d" % (
        name, len(gs), min(gs), max(gs), max(gs)-min(gs),
        max(steps) if steps else 0.0, wi, wi+1,
        sum(1 for s in segs if s["floor"]),
        min(s["decl"] for s in segs),
        sum(1 for s in segs if s["fin"] != 0.0)))
    for k in range(len(gs)-1):
        print("   step u%d(%s)->u%d(%s): %+.2fdB" % (
            segs[k]["i"], segs[k]["sym"].encode("unicode_escape").decode("ascii"),
            segs[k+1]["i"], segs[k+1]["sym"].encode("unicode_escape").decode("ascii"),
            gs[k+1]-gs[k]))
print("GLOBAL planned: min=%.2f max=%.2f spread=%.2f n=%d floor_n=%d (>=floor -6: %d) near0(>=-1)=%d" % (
    min(allg), max(allg), max(allg)-min(allg), len(allg), floorn,
    sum(1 for g in allg if g <= -5.99), neardb))

print("=== PER-ARM (planned, incl decl/fin/floor) ===")
from collections import defaultdict
arms = defaultdict(list)
for segs in items.values():
    for s in segs:
        arms[s["arm"]].append(s["g"])
for a in sorted(arms):
    v = np.array(arms[a])
    print("   %-18s n=%2d min=%6.2f max=%6.2f mean=%6.2f" % (a, len(v), v.min(), v.max(), v.mean()))

print("=== FLOOR HITS (-6) ===")
for name, segs in items.items():
    hit = [s for s in segs if s["floor"]]
    if hit:
        print("   %s: %s" % (name, ", ".join(
            "u%d(%s,%s,base=%.1f,decl=%.1f,fin=%.1f)" % (
                s["i"], s["sym"].encode("unicode_escape").decode("ascii"),
                s["arm"], s["base"], s["decl"], s["fin"]) for s in hit)))

print("=== DECLINATION CAP (idx>=12 -> decl=-6.0) ===")
capped = [(n, s) for n, segs in items.items() for s in segs if s["decl"] <= -5.99]
print("   segments at decl cap: %d" % len(capped))
for n, s in capped:
    print("   %s u%d(%s): decl=%.1f" % (n, s["i"], s["sym"].encode("unicode_escape").decode("ascii"), s["decl"]))
print("   deepest decl in corpus: %.1f dB" % min(s["decl"] for segs in items.values() for s in segs))

print("=== UNCLIPPED SPREAD (base+decl+fin, floor removed) ===")
raw_min, raw_max = 1e9, -1e9
for segs in items.values():
    for s in segs:
        raw = s["base"] + s["decl"] + s["fin"]
        raw_min = min(raw_min, raw); raw_max = max(raw_max, raw)
print("   min=%.2f max=%.2f spread=%.2f; floor hides %.2fdB" % (
    raw_min, raw_max, raw_max-raw_min, (raw_max-raw_min)-(max(allg)-min(allg))))

print("=== DYNAMIC-RANGE SPLIT (planned side) ===")
bases = sorted(set(s["base"] for segs in items.values() for s in segs))
print("   arm-base values in corpus: %s (range %.1f dB)" % (bases, max(bases)-min(bases)))
decls = sorted(set(s["decl"] for segs in items.values() for s in segs))
print("   decl values in corpus: min %.1f max %.1f (range %.1f dB)" % (min(decls), max(decls), max(decls)-min(decls)))
fins = sorted(set(s["fin"] for segs in items.values() for s in segs))
print("   fin values in corpus: %s" % fins)
print("   FINAL FADE (post-gain, engine FINAL_FADE_DB=-12dB over final<=150ms): up to -12dB depth on the final segment tail")
