"""0.0.0.28.1 part 4: where is the global max? segment ownership of peak
samples + s1-window content split (h-tail vs E-onset). Uses f32 renders."""
import re, os
import numpy as np

ROOT = r"E:\01_coding\ARTicul"
P = os.path.join(ROOT, "probe", "0.0.0.28.1")
SR = 22050
WIN = SR // 50

items, cur = {}, None
for line in open(os.path.join(P, "plan.txt"), encoding="utf8"):
    line = line.rstrip("\n")
    m = re.match(r"== (.+?) :: (.*)", line)
    if m:
        cur = m.group(1); items[cur] = {"text": m.group(2), "segs": []}
        continue
    m = re.match(r"u(\d+) sym=(.*?) dur=(\d+)ms stress=(\S+) word_final=(\S+) pause=(\S+) seglen=(\d+) arm=(\S+) base=(\S+) decl=(\S+) fin=(\S+) floor=(\d+) engine=(\S+)dB match=(\S+)", line)
    if m and cur is not None:
        items[cur]["segs"].append({"i": int(m.group(1)), "sym": m.group(2),
            "arm": m.group(8), "seglen": int(m.group(7))})

def loadf(name):
    return np.fromfile(os.path.join(P, name + ".f32"), dtype=np.float32).astype(np.float64)

def seg_spans(itemname, n):
    segs = items[itemname]["segs"]
    # output-domain spans with GOAT merge + fade overlap (approx: no-overlap partition
    # by cumulative seglen minus fades, same as starts logic)
    groups, i = [], 0
    while i < len(segs):
        if (i+1 < len(segs) and segs[i]["arm"] == "stressed-vowel" and segs[i]["sym"] == "o"
                and segs[i+1]["arm"] == "unstressed-vowel"):
            groups.append([i, i+1]); i += 2
        else:
            groups.append([i]); i += 1
    lens = [sum(segs[j]["seglen"] for j in g) for g in groups]
    starts = [0]; pos = 0
    for gi in range(1, len(groups)):
        pos = pos + lens[gi-1] - 176
        starts.append(pos)
    return groups, starts, lens

for name in ["demo_hello", "annyeong", "yeobo", "fixed_sentence", "cluster_probe"]:
    y = loadf(name)
    n = len(y)
    amax = int(np.argmax(np.abs(y)))
    groups, starts, lens = seg_spans(name, n)
    # owning group
    og = max([gi for gi, s in enumerate(starts) if s <= amax])
    print("%s n=%d globalmax pos=%d (|y|=%.4f) group=%d lens=%s" % (
        name, n, amax, abs(y[amax]), og, lens))
    # top-12 peak positions
    order = np.argsort(-np.abs(y))[:12]
    print("   top12 pos: %s" % (" ".join("%d(%.3f)" % (p, abs(y[p])) for p in order)))
    # s1 window split for hello: h-tail [1544,1720) vs E-onset [1720,...)
    if name == "demo_hello":
        print("   s1win [1544,1764): max=%.4f at %d" % (
            np.max(np.abs(y[1544:1764])), 1544+int(np.argmax(np.abs(y[1544:1764])))))
        print("   h-tail [1544,1720): max=%.4f | E-onset [1720,1900): max=%.4f" % (
            np.max(np.abs(y[1544:1720])), np.max(np.abs(y[1720:1900]))))
