"""0.0.0.28.1 part 2: spark windows, trough-gate windows, proposal prediction."""
import re, wave, os
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
        items[cur]["segs"].append({
            "i": int(m.group(1)), "sym": m.group(2), "dur": int(m.group(3)),
            "stress": m.group(4), "arm": m.group(8), "base": float(m.group(9)),
            "decl": float(m.group(10)), "fin": float(m.group(11)),
            "floor": int(m.group(12)), "g": float(m.group(13)), "seglen": int(m.group(7)),
        })

VOWEL_ARMS = ("stressed-vowel", "unstressed-vowel")

def work_starts(segs):
    # work groups with GOAT merge: stressed o + unstressed U merge (hello only)
    groups, i = [], 0
    while i < len(segs):
        if (i + 1 < len(segs) and segs[i]["arm"] == "stressed-vowel"
                and segs[i]["sym"] == "o" and segs[i+1]["arm"] == "unstressed-vowel"):
            groups.append([i, i+1]); i += 2
        else:
            groups.append([i]); i += 1
    lens = [sum(segs[j]["seglen"] for j in g) for g in groups]
    starts, pos = [0], 0
    for gi in range(1, len(groups)):
        a = groups[gi-1][-1]; b = groups[gi][0]
        vv = segs[a]["arm"] in VOWEL_ARMS and segs[b]["arm"] in VOWEL_ARMS
        fade = 1102 if vv else 176
        pos = pos + lens[gi-1] - min(fade, pos + lens[gi-1] if False else fade)
        # mirror gate: pos -= fade.min(pos) AFTER previous pos+=lens; recompute cleanly below
        starts.append(None)
    # clean recompute mirroring the gate loop exactly
    pos = 0; starts = [0]
    for gi in range(1, len(groups)):
        a = groups[gi-1][-1]; b = groups[gi][0]
        vv = segs[a]["arm"] in VOWEL_ARMS and segs[b]["arm"] in VOWEL_ARMS
        fade = 1102 if vv else 176
        pos = pos + lens[gi-1]
        pos -= min(fade, pos)
        starts.append(pos)
    return groups, lens, starts

def load(name):
    w = wave.open(os.path.join(P, name + ".wav"), "rb")
    n = w.getnframes()
    x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float64) / 32768.0
    return n, x

d = np.load(os.path.join(P, "makeup.npz"))
# per-file window gains gdb recompute from saved g
def gdb_of(g):
    return 20*np.log10(np.maximum(g, 1e-12))

print("=== SPARK WINDOWS (10ms from non-initial segment starts, gate mirror) ===")
for name in ["demo_hello", "annyeong", "yeobo"]:
    n, x = load(name)
    g = d[name + ".npy"] if False else d[name]
    G = float(d[name + "_G"][0])
    gdb = gdb_of(g)
    segs = items[{"demo_hello": "demo_hello", "annyeong": "annyeong", "yeobo": "yeobo"}[name]]["segs"]
    groups, lens, starts = work_starts(segs)
    win = round(10/1000*SR)
    print("%s groups=%d lens=%s" % (name, len(groups), lens))
    for gi in range(1, len(groups)):
        s0 = min(starts[gi], n-1)
        seg = x[s0:s0+win]
        uncl = seg[np.abs(seg) < 0.985]
        pk = float(np.max(np.abs(uncl))) if len(uncl) else 0.0
        nc = int((np.abs(seg) >= 0.985).sum())
        li = min(int(s0/WIN), len(g)-1)
        # estimated pre-leveler peak in window via inversion ratio
        pre_pk = pk / (g[li]*G) if g[li]*G > 1e-9 else 0.0
        print("   start%d pos=%5d seg=%s makeup=%6.2fdB lift=%.2fx uncl=%.4f pre_est=%.4f clamp_n=%d %s" % (
            gi, s0, segs[groups[gi][0]]["sym"].encode("unicode_escape").decode("ascii"),
            gdb[li], g[li]*G, pk, pre_pk, nc,
            "SPARK" if (pk >= 0.9 or nc) else "ok"))

print("=== TROUGH-GATE WINDOWS (k with dip < -6dB, makeup there) ===")
for name in ["demo_hello", "annyeong", "yeobo", "fixed_sentence", "cluster_probe"]:
    n, x = load(name)
    g = d[name]; G = float(d[name + "_G"][0]); gdb = gdb_of(g)
    wlen = SR//100; nw2 = n//wlen
    nr = np.sqrt((x[:nw2*wlen].reshape(nw2, wlen)**2).mean(axis=1))
    rows = []
    for k in range(10, nw2-15):
        ctx = float(nr[k-10:k].mean())
        if ctx <= 1e-9 or nr[k] <= 1e-9:
            continue
        dip = 20.0*np.log10(float(nr[k])/ctx)
        if dip < -6.0:
            li = min(int((k*wlen)/WIN), len(g)-1)
            rows.append((k, dip, gdb[li], g[li]*G))
    print("%s deep-dip windows (n=%d):" % (name, len(rows)))
    for k, dip, mu, lift in rows[:14]:
        print("   k=%3d t=%.3fs dip=%6.2fdB makeup=%6.2fdB lift=%.2fx" % (k, k*wlen/SR, dip, mu, lift))

print("=== PER-WINDOW TRAJECTORIES (demos: edb/gdb/lift) ===")
for name in ["demo_hello", "annyeong", "yeobo"]:
    g = d[name]; G = float(d[name + "_G"][0]); gdb = gdb_of(g)
    print("%s inw=%d G=%.4f" % (name, len(g), G))
    print("   gdb: " + " ".join("%5.1f" % v for v in gdb))
