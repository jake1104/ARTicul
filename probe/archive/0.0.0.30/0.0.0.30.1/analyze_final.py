"""0.0.0.30.1 part 6: finalist detail. F3d25/F4d10 + cap12 + pre{1.10,1.25} +
coh ON. Full gate panel + margins + makeup + DR split + table steps."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(r"E:\01_coding\ARTicul", "probe", "0.0.0.30.1"))
from gchain import *
from analyze_flat import (TABLES, new_gain, is_vowel_seg, is_fric_seg,
                          delta_track, load_y, word_spans, word_db, items, d, NAMES)
from analyze_flat2 import TABLES2, apa_ratio, APA, APA_GEOM, APA_PRE, APA_Y

FINAL = [
    ("P1", TABLES2["F3d25"], 12.0, 1.25, True),
    ("P2", TABLES2["F4d10"], 12.0, 1.25, True),
    ("P0", TABLES2["F3d25"], 12.0, 1.10, True),
]

for combo, T, cap, pre, coh in FINAL:
    print("=" * 70)
    print("COMBO %s arms=%s cap=%.0f pre=%.2f coh=%s" % (combo, "F3d25" if T is TABLES2["F3d25"] else "F4d10", cap, pre, coh))
    allg = []
    for name in NAMES:
        segs = items[name]["segs"]
        allg += [new_gain(s, s["i"], len(segs), T) for s in segs]
    print("eff planned spread: min=%.2f max=%.2f spread=%.2f" % (min(allg), max(allg), max(allg) - min(allg)))
    steps = []
    for name in NAMES:
        segs = items[name]["segs"]
        gs = [new_gain(s, s["i"], len(segs), T) for s in segs]
        steps += [abs(gs[k + 1] - gs[k]) for k in range(len(gs) - 1)]
    print("max adjacent table step: %.2f dB (junction bound 5.0)" % max(steps))
    fl = [(name, [(s["i"], s["arm"]) for s in items[name]["segs"]
                  if abs(new_gain(s, s["i"], len(items[name]["segs"]), T) + T["floor"]) < 1e-9])
          for name in NAMES]
    print("floor(-6) hits: %s" % [(n, v) for n, v in fl if v])
    for name in ["demo_hello", "annyeong", "yeobo"]:
        y = load_y(name)
        segs = items[name]["segs"]
        geom = work_geometry(segs)
        pre2 = d[name + "_pre"] * 10.0 ** (delta_track(len(y), segs, geom, T) / 20.0)
        f, info = forward_full(pre2, segs, geom, cap, pre, True)
        n = len(f)
        halves = 20 * np.log10(max(rms(f[n // 2:]), 1e-9)) - 20 * np.log10(max(rms(f[:n // 2]), 1e-9))
        sp = spark_windows(f, geom)
        worst = max(v for _, _, v, _ in sp)
        nc = int((np.abs(f) >= 0.985).sum())
        tail = rms(f[2 * (n // 3):])
        print("%s halves=%+.2f(<=5) trough=%+.2f(>=-14) rms=%.4f(>=0.095,>=0.10?) tail=%.4f sparkmax=%.4f(<0.9) clamp=%d" % (
            name, halves, trough_max_db(f), rms(f), tail, worst, nc))
        for gi, s0, pk, cl in sp:
            print("    s%d pos=%d pk=%.4f cl=%d" % (gi, s0, pk, cl))
        g = info["g"]
        print("    makeup dB max=%.2f mean=%.2f min=%.2f capfrac=%.3f G=%+.2fdB" % (
            info["gdb"].max(), info["gdb"].mean(), info["gdb"].min(),
            (info["gdb"] >= cap - 0.01).mean(), 20 * np.log10(info["G"])))
        cg = info["cgains"]
        print("    coherence dB min=%+.2f max=%+.2f" % (20 * np.log10(cg.min()), 20 * np.log10(cg.max())))
        groups, lens_g, starts_g = geom["groups"], geom["lens"], geom["starts"]
        for gi in range(1, len(groups)):
            if any(is_fric_seg(segs[oi]) for oi in groups[gi - 1]) or any(is_fric_seg(segs[oi]) for oi in groups[gi]):
                continue
            a = f[starts_g[gi - 1] + min(220, len(f)):starts_g[gi - 1] + lens_g[gi - 1] - 220]
            b = f[starts_g[gi] + 220:starts_g[gi] + lens_g[gi] - 220]
            if len(a) < 16 or len(b) < 16:
                continue
            step = 20 * np.log10(max(rms(b), 1e-9)) - 20 * np.log10(max(rms(a), 1e-9))
            if abs(step) > 3.0:
                print("    cohstep b%d %+.2f" % (gi, step))
    for name in ["demo_hello", "old_input"]:
        y = load_y(name)
        segs = items[name]["segs"]
        geom = work_geometry(segs)
        pre2 = d[name + "_pre"] * 10.0 ** (delta_track(len(y), segs, geom, T) / 20.0)
        f, _ = forward_full(pre2, segs, geom, cap, pre, True)
        wb = word_spans(name, segs)
        diff = word_db(f, *wb[1]) - word_db(f, *wb[0])
        print("%s balance diff=%+.2f %s" % (name, diff, "(violator LOST)" if name == "old_input" and diff >= -6.0 else ""))
    dd = delta_track(len(APA_Y), APA, APA_GEOM, T)
    fapa, _ = forward_full(APA_PRE * 10.0 ** (dd / 20.0), APA, APA_GEOM, cap, pre, True)
    print("apa_testplan ratio=%.3f (>1.8)" % apa_ratio(fapa))
    f = None
    y = load_y("demo_hello")
    segs = items["demo_hello"]["segs"]
    geom = work_geometry(segs)
    pre2 = d["demo_hello_pre"] * 10.0 ** (delta_track(len(y), segs, geom, T) / 20.0)
    f, _ = forward_full(pre2, segs, geom, cap, pre, True)
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
    print("hello lateral gap=%.2f (<8)" % (
        20 * np.log10(max(rms(f[vs:ve]), 1e-9)) - 20 * np.log10(max(rms(f[ws:we]), 1e-9))))
    for name in ["fixed_sentence", "creak_probe", "gain_probe", "cluster_probe", "pause_probe"]:
        y = load_y(name)
        segs = items[name]["segs"]
        geom = work_geometry(segs)
        pre2 = d[name + "_pre"] * 10.0 ** (delta_track(len(y), segs, geom, T) / 20.0)
        f, _ = forward_full(pre2, segs, geom, cap, pre, True)
        print("%s eval rms=%.4f (report-only)" % (name, rms(f)))
print("done final")
