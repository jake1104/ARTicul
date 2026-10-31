"""0.0.0.30.1 part 7: peak-setter grid. F3d25/F4d10 x sib {-2/-1.5,-4,-6,-8}
x cap {8,12}, pre 1.10, coh ON. Cooling /s/ (the measured peak-setter)
should raise G and cut tail-rescue need."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(r"E:\01_coding\ARTicul", "probe", "0.0.0.30.1"))
from gchain import *
from analyze_flat import (TABLES, new_gain, is_vowel_seg, is_fric_seg,
                          delta_track, load_y, word_spans, word_db, items, d, NAMES)
from analyze_flat2 import TABLES2, apa_ratio, APA, APA_GEOM, APA_PRE, APA_Y
from analyze_flat3 import full_gates

for tname in ["F3d25", "F4d10"]:
    for sib in ([-2.0, -4.0, -6.0, -8.0] if tname == "F3d25" else [-1.5, -4.0, -6.0, -8.0]):
        for cap in (8.0, 12.0):
            T = dict(TABLES2[tname]); T["sib"] = sib
            line = ["%s sib%g cap%d" % (tname, sib, cap)]
            ok = True
            for name in ["demo_hello", "annyeong", "yeobo"]:
                y = load_y(name)
                segs = items[name]["segs"]
                geom = work_geometry(segs)
                pre2 = d[name + "_pre"] * 10.0 ** (delta_track(len(y), segs, geom, T) / 20.0)
                f, info = forward_full(pre2, segs, geom, cap, 1.10, True)
                m = full_gates(f, name, segs, geom)
                flag = ""
                good = abs(m["halves"]) <= 5.0 and m["trough"] >= -14.0 and m["rms"] >= 0.095 and m["spark"] < 0.9 and m["cohviol"] == 0
                if name == "yeobo":
                    good = good and m["tail"] >= 0.03
                if not good:
                    flag = " FAIL"
                    ok = False
                line.append("%s h=%+.1f t=%+.1f r=%.3f tl=%.3f sp=%.4f cl=%d cv=%d G=%+.1f mkmax=%.0f%s" % (
                    name[:2], m["halves"], m["trough"], m["rms"], m["tail"],
                    m["spark"], m["clamp"], m["cohviol"],
                    20 * np.log10(info["G"]), info["gdb"].max(), flag))
            dd = delta_track(len(APA_Y), APA, APA_GEOM, T)
            fapa, _ = forward_full(APA_PRE * 10.0 ** (dd / 20.0), APA, APA_GEOM, cap, 1.10, True)
            ar = apa_ratio(fapa)
            line.append("apa=%.2f%s" % (ar, " FAIL" if ar <= 1.8 else ""))
            if ar <= 1.8:
                ok = False
            y = load_y("old_input")
            segs = items["old_input"]["segs"]
            geom = work_geometry(segs)
            pre2 = d["old_input_pre"] * 10.0 ** (delta_track(len(y), segs, geom, T) / 20.0)
            fo, _ = forward_full(pre2, segs, geom, cap, 1.10, True)
            wb = word_spans("old_input", segs)
            diff = word_db(fo, *wb[1]) - word_db(fo, *wb[0])
            line.append("oldpin=%+.2f%s" % (diff, "" if diff < -6.0 else " LOST"))
            line.append("ALLPASS" if ok else "")
            print(" | ".join(line))
print("done grid4")
