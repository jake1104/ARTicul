"""0.0.0.30.1 part 4: extended FLAT grid (coh OFF, prescale 0.90).
Tables F3/F4 x decl {0.25, 0.10, 0} x cap {6, 8, 10}. Includes apa-testplan
sim (bespoke Primary marks) for the gain.rs ratio gate."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(r"E:\01_coding\ARTicul", "probe", "0.0.0.30.1"))
from gchain import *
from analyze_flat import (TABLES, arm_base, new_gain, is_vowel_seg, is_fric_seg,
                          delta_track, load_y, word_spans, word_db, items, d, NAMES)

F4 = dict(strV=0.0, unstrV=-0.75, sib=-1.5, approx=-2.0, nasal=-2.5, h=-8.0,
          weak=-4.0, voff=-5.0, latU=-6.0, latV=-8.0, aspmax=-1.5,
          decl=0.25, declcap=12, fin=2.0, floor=6.0)
TABLES2 = {
    "F3d25": dict(TABLES["F3"], decl=0.25),
    "F4d25": dict(F4, decl=0.25),
    "F3d10": dict(TABLES["F3"], decl=0.10),
    "F4d10": dict(F4, decl=0.10),
    "F3d00": dict(TABLES["F3"], decl=0.0),
    "F4d00": dict(F4, decl=0.0),
}
CAPS = [6.0, 8.0, 10.0]
PRE = 0.95 if False else 0.90

# apa testplan segs (ratiodump): durations/gains/stresses mirrored
APA = [
    {"sym": "a", "dur": 139, "stress": "Primary", "pause": False,
     "seglen": 3065, "arm": "stressed-vowel",
     "base": 0.0, "decl": 0.0, "fin": 0.0, "floor": 0, "g": 0.0, "i": 0},
    {"sym": "p", "dur": 52, "stress": "Unstressed", "pause": False,
     "seglen": 1147, "arm": "other-stop",
     "base": 0.0, "decl": -0.5, "fin": 0.0, "floor": 0, "g": -0.5, "i": 1},
    {"sym": "a", "dur": 102, "stress": "Unstressed", "pause": False,
     "seglen": 2249, "arm": "unstressed-vowel",
     "base": -1.75, "decl": -1.0, "fin": 0.0, "floor": 0, "g": -2.75, "i": 2},
]
APA_GEOM = {"groups": [[0], [1], [2]], "lens": [3065, 1147, 2249],
            "starts": [0, 3065 - 176, 3065 - 176 + 1147 - 176],
            "fades": [0, 176, 176],
            "seg_ranges": [(0, 3065), (3065 - 176, 3065 - 176 + 1147),
                           (3065 - 176 + 1147 - 176, 3065 - 176 + 1147 - 176 + 2249)]}
APA_Y = np.fromfile(os.path.join(P, "apa_testplan.f32"), dtype=np.float32).astype(np.float64)
APA_PRE, APA_INFO, APA_RESID = invert_full(APA_Y, APA, APA_GEOM, iters=150,
                                           cap_db=12.0, prescale=1.10, coherence=True)
print("apa testplan inversion resid=%.2e (f32 domain, coherence ON)" % APA_RESID)


def apa_ratio(f):
    st2 = APA_GEOM["starts"][2]
    w0 = f[500:1500]
    w2 = f[st2 + 300:st2 + 1300]
    return rms(w0) / max(rms(w2), 1e-9)


for tname, T in TABLES2.items():
    allg = []
    for name in NAMES:
        segs = items[name]["segs"]
        allg += [new_gain(s, s["i"], len(segs), T) for s in segs]
    fl = sum(1 for name in NAMES for s in items[name]["segs"]
             if abs(new_gain(s, s["i"], len(items[name]["segs"]), T) + T["floor"]) < 1e-9
             and (s["base"] + (-min(s["i"], T["declcap"]) * T["decl"])) < -T["floor"] + 1e-9)
    print("%s eff spread %.2f..%.2f = %.2f dB" % (tname, min(allg), max(allg), max(allg) - min(allg)))

print("=== GRID (coh OFF, prescale 0.90) ===")
for tname, T in TABLES2.items():
    for cap in CAPS:
        line = [tname, "cap%d" % cap]
        res = {}
        for name in NAMES:
            y = load_y(name)
            segs = items[name]["segs"]
            geom = work_geometry(segs)
            pre2 = d[name + "_pre"] * 10.0 ** (delta_track(len(y), segs, geom, T) / 20.0)
            f, info = forward_full(pre2, segs, geom, cap, PRE, False)
            res[name] = (f, info)
        for name in ["demo_hello", "annyeong", "yeobo"]:
            f, info = res[name]
            n = len(f)
            halves = 20 * np.log10(max(rms(f[n // 2:]), 1e-9)) - 20 * np.log10(max(rms(f[:n // 2]), 1e-9))
            line.append("%s h=%+.1f t=%+.1f r=%.3f tail=%.3f cl=%d" % (
                name[:2], halves, trough_max_db(f), rms(f), rms(f[2 * (n // 3):]),
                int((np.abs(f) >= 0.985).sum())))
        f, info = res["old_input"]
        wb = word_spans("old_input", items["old_input"]["segs"])
        diff = word_db(f, *wb[1]) - word_db(f, *wb[0])
        line.append("oldpin=%+.2f%s" % (diff, " LOST" if diff >= -6.0 else ""))
        # apa testplan ratio under this table
        dd = delta_track(len(APA_Y), APA, APA_GEOM, T)
        fapa, _ = forward_full(APA_PRE * 10.0 ** (dd / 20.0), APA, APA_GEOM, cap, PRE, False)
        line.append("apa=%.2f%s" % (apa_ratio(fapa), " FAIL" if apa_ratio(fapa) <= 1.8 else ""))
        # lateral gap hello
        f = res["demo_hello"][0]
        segs = items["demo_hello"]["segs"]
        li = next(i for i, s in enumerate(segs) if s["arm"] == "approximant")
        oi = next(i for i, s in enumerate(segs) if s["stress"] != "Unstressed" and is_vowel_seg(s))
        lens = [s["seglen"] for s in segs]
        fades = [0] * len(segs)
        for i in range(1, len(segs)):
            fades[i] = 1102 if (is_vowel_seg(segs[i - 1]) and is_vowel_seg(segs[i])) else 176
        starts = [0]
        for i in range(1, len(segs)):
            starts.append(starts[i - 1] + lens[i - 1] - min(fades[i], starts[i - 1] + lens[i - 1]))
        n = len(f)
        nf = fades[li + 1] if li + 1 < len(segs) else 0
        ws, we = starts[li] + fades[li] + 110, min(starts[li] + lens[li] - nf - 110, n)
        of = fades[oi + 1] if oi + 1 < len(segs) else 0
        vs, ve = starts[oi] + fades[oi] + 110, min(starts[oi] + lens[oi] - of - 110, n)
        gap = 20 * np.log10(max(rms(f[vs:ve]), 1e-9)) - 20 * np.log10(max(rms(f[ws:we]), 1e-9))
        line.append("latgap=%.1f%s" % (gap, " FAIL" if gap >= 8.0 else ""))
        # coherence-RMS steps on sim output
        viol = []
        for name in ["demo_hello", "annyeong", "yeobo"]:
            f = res[name][0]
            segs = items[name]["segs"]
            groups, lens_g, starts_g = work_geometry(segs)["groups"], work_geometry(segs)["lens"], work_geometry(segs)["starts"]
            for gi in range(1, len(groups)):
                if any(is_fric_seg(segs[oi]) for oi in groups[gi - 1]) or any(is_fric_seg(segs[oi]) for oi in groups[gi]):
                    continue
                (s0, l0) = (starts_g[gi - 1], lens_g[gi - 1])
                (t0, l1) = (starts_g[gi], lens_g[gi])
                a = f[s0 + min(220, len(f)):s0 + l0 - 220]
                b = f[t0 + 220:t0 + l1 - 220]
                if len(a) < 16 or len(b) < 16:
                    continue
                step = 20 * np.log10(max(rms(b), 1e-9)) - 20 * np.log10(max(rms(a), 1e-9))
                if abs(step) > 4.0:
                    viol.append("%s b%d %+.1f" % (name[:2], gi, step))
        line.append("cohviol=%d%s" % (len(viol), (" " + ",".join(viol)) if viol else ""))
        # rescue need: max makeup dB on demos
        mk = ["%s mk=%.0f" % (name[:2], res[name][1]["gdb"].max()) for name in ["demo_hello", "annyeong", "yeobo"]]
        line.append(" ".join(mk))
        print(" | ".join(line))
print("done grid2")
