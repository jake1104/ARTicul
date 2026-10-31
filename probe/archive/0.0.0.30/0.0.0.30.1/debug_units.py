import os, sys
import numpy as np
sys.path.insert(0, os.path.join(r"E:\01_coding\ARTicul", "probe", "0.0.0.30.1"))
from gchain import *
from analyze_flat import (new_gain, is_vowel_seg, delta_track, load_y, items, d)
from analyze_flat2 import TABLES2
T = TABLES2["F4d10"]
for name in ["annyeong", "yeobo"]:
    y = load_y(name)
    segs = items[name]["segs"]
    geom = work_geometry(segs)
    pre2 = d[name + "_pre"] * 10.0 ** (delta_track(len(y), segs, geom, T) / 20.0)
    f, info = forward_full(pre2, segs, geom, 8.0, 0.90, False)
    print("== %s F4d10 cap8 pre0.90 cohOFF (annyeong halves driver hunt)" % name)
    for gi, g in enumerate(geom["groups"]):
        s0 = geom["starts"][gi]
        s1 = min(s0 + geom["lens"][gi], len(f))
        seg = f[s0:s1]
        gs = ["%+.1f" % new_gain(segs[oi], oi, len(segs), T) for oi in g]
        syms = ",".join(segs[oi]["sym"] for oi in g)
        print("  u%d(%s) dur=%dms gain=%s outRMS=%.4f (%+.1fdBFS)" % (
            gi, syms.encode("unicode_escape").decode("ascii"),
            sum(segs[oi]["dur"] for oi in g), "/".join(gs),
            rms(seg), 20 * np.log10(max(rms(seg), 1e-9))))
