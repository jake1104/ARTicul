"""0.0.0.30.1 part 8: rescue-redistribution grid. Move tail rescue from
blocky coherence gains to smooth leveler makeup: coh_cap {6,3,2} x
levelcap {12,14,16}, F3d25 table, pre 1.10, coh ON."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(r"E:\01_coding\ARTicul", "probe", "0.0.0.30.1"))
from gchain import *
from analyze_flat import (new_gain, delta_track, load_y, word_spans, word_db, items, d)
from analyze_flat2 import TABLES2, apa_ratio, APA, APA_GEOM, APA_PRE, APA_Y
from analyze_flat3 import full_gates

T = TABLES2["F3d25"]
for coh_cap in (6.0, 3.0, 2.0):
    for levelcap in (12.0, 14.0, 16.0):
        line = ["cohcap%g lvlcap%d" % (coh_cap, levelcap)]
        ok = True
        for name in ["demo_hello", "annyeong", "yeobo"]:
            y = load_y(name)
            segs = items[name]["segs"]
            geom = work_geometry(segs)
            pre2 = d[name + "_pre"] * 10.0 ** (delta_track(len(y), segs, geom, T) / 20.0)
            f, info = forward_full(pre2, segs, geom, levelcap, 1.10, True, coh_cap)
            m = full_gates(f, name, segs, geom)
            flag = ""
            good = abs(m["halves"]) <= 5.0 and m["trough"] >= -14.0 and m["rms"] >= 0.095 and m["spark"] < 0.9 and m["cohviol"] == 0
            if name == "yeobo":
                good = good and m["tail"] >= 0.03
            if not good:
                flag = " FAIL"
                ok = False
            line.append("%s h=%+.1f t=%+.1f r=%.3f tl=%.3f sp=%.4f cl=%d cv=%d%s" % (
                name[:2], m["halves"], m["trough"], m["rms"], m["tail"],
                m["spark"], m["clamp"], m["cohviol"], flag))
        dd = delta_track(len(APA_Y), APA, APA_GEOM, T)
        fapa, _ = forward_full(APA_PRE * 10.0 ** (dd / 20.0), APA, APA_GEOM, levelcap, 1.10, True, coh_cap)
        ar = apa_ratio(fapa)
        line.append("apa=%.2f%s" % (ar, " FAIL" if ar <= 1.8 else ""))
        line.append("ALLPASS" if ok else "")
        print(" | ".join(line))
print("done grid5")
