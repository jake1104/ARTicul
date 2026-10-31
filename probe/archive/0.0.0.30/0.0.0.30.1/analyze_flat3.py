"""0.0.0.30.1 part 5: expanded-scope grid (Option 1 feasibility) + Option 2
refinement. Option 1: fade {-12,-8,-6} x h-base {-8,-6,-4} x cap {6,8},
F4d10 table, pre 0.90, coh OFF. Option 2: coh ON x cap {8,10} x pre
{0.95,1.10} on F3d25/F4d10."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(r"E:\01_coding\ARTicul", "probe", "0.0.0.30.1"))
from gchain import *
from analyze_flat import (TABLES, arm_base, new_gain, is_vowel_seg, is_fric_seg,
                          delta_track, load_y, word_spans, word_db, items, d, NAMES)
from analyze_flat2 import TABLES2, PRE, apa_ratio, APA, APA_GEOM, APA_PRE, APA_Y

F4d10 = TABLES2["F4d10"]
F3d25 = TABLES2["F3d25"]


def fade_remap(n, final_ms, old_floor_db, new_floor_db):
    k = min(int(150.0 / 1000.0 * SR), int(round(final_ms / 1000.0 * SR)))
    k = max(min(k, n), 0)
    if k == 0:
        return np.ones(n)
    t = np.arange(k) / max(k, 1)
    shape = 0.5 * (1.0 + np.cos(np.pi * t))
    fo = 10.0 ** (old_floor_db / 20.0)
    fn = 10.0 ** (new_floor_db / 20.0)
    mo = fo + (1.0 - fo) * shape
    mn = fn + (1.0 - fn) * shape
    m = np.ones(n)
    m[n - k:] = mn / np.maximum(mo, 1e-9)
    return m


def combo_metrics(f, name, segs, geom):
    n = len(f)
    h0, h1 = rms(f[:n // 2]), rms(f[n // 2:])
    halves = 20 * np.log10(max(h1, 1e-9)) - 20 * np.log10(max(h0, 1e-9))
    sp = spark_windows(f, geom)
    worst = max(v for _, _, v, _ in sp)
    return (halves, trough_max_db(f), rms(f), rms(f[2 * (n // 3):]), worst,
            int((np.abs(f) >= 0.985).sum()))


def full_gates(f, name, segs, geom):
    out = {}
    h, t, r, tail, w, cl = combo_metrics(f, name, segs, geom)
    out.update(dict(halves=h, trough=t, rms=r, tail=tail, spark=w, clamp=cl))
    groups, lens_g, starts_g = geom["groups"], geom["lens"], geom["starts"]
    viol = 0
    for gi in range(1, len(groups)):
        if any(is_fric_seg(segs[oi]) for oi in groups[gi - 1]) or any(is_fric_seg(segs[oi]) for oi in groups[gi]):
            continue
        a = f[starts_g[gi - 1] + min(220, len(f)):starts_g[gi - 1] + lens_g[gi - 1] - 220]
        b = f[starts_g[gi] + 220:starts_g[gi] + lens_g[gi] - 220]
        if len(a) < 16 or len(b) < 16:
            continue
        if abs(20 * np.log10(max(rms(b), 1e-9)) - 20 * np.log10(max(rms(a), 1e-9))) > 4.0:
            viol += 1
    out["cohviol"] = viol
    return out


print("=== OPTION 1: F4d10 + fade/h variants, pre 0.90, coh OFF ===")
for fade_db in (-12.0, -8.0, -6.0):
    for hbase in (-8.0, -6.0, -4.0):
        for cap in (6.0, 8.0):
            T = dict(F4d10)
            line = ["fade%g h%g cap%d" % (fade_db, hbase, cap)]
            ok = True
            for name in NAMES:
                y = load_y(name)
                segs = items[name]["segs"]
                geom = work_geometry(segs)
                dd = delta_track(len(y), segs, geom, T)
                # h override: recompute h segs with hbase
                for s in segs:
                    if s["arm"] == "h-fric":
                        dd[geom["seg_ranges"][s["i"]][0]:geom["seg_ranges"][s["i"]][1]] = (
                            max(hbase + (-min(s["i"], T["declcap"]) * T["decl"]), -T["floor"]) - s["g"])
                pre2 = d[name + "_pre"] * 10.0 ** (dd / 20.0)
                fms = segs[-1]["dur"]
                pre2 = pre2 * fade_remap(len(y), fms, -12.0, fade_db)
                f, info = forward_full(pre2, segs, geom, cap, 0.90, False)
                if name in ("demo_hello", "annyeong", "yeobo"):
                    m = full_gates(f, name, segs, geom)
                    flag = ""
                    if abs(m["halves"]) > 5.0 or m["trough"] < -14.0 or m["rms"] < 0.095 or m["clamp"] > 0 or m["spark"] >= 0.9 or m["cohviol"] > 0:
                        flag = " FAIL"
                        ok = False
                    if name == "yeobo" and m["tail"] < 0.03:
                        flag += "(tail)"
                        ok = False
                    line.append("%s h=%+.1f t=%+.1f r=%.3f tl=%.3f sp=%.3f cl=%d cv=%d%s" % (
                        name[:2], m["halves"], m["trough"], m["rms"], m["tail"],
                        m["spark"], m["clamp"], m["cohviol"], flag))
            # old pin + apa + lateral
            f, _, _ = None, None, None
            y = load_y("old_input")
            segs = items["old_input"]["segs"]
            geom = work_geometry(segs)
            dd = delta_track(len(y), segs, geom, T)
            for s in segs:
                if s["arm"] == "h-fric":
                    dd[geom["seg_ranges"][s["i"]][0]:geom["seg_ranges"][s["i"]][1]] = (
                        max(hbase + (-min(s["i"], T["declcap"]) * T["decl"]), -T["floor"]) - s["g"])
            pre2 = d["old_input_pre"] * 10.0 ** (dd / 20.0)
            pre2 = pre2 * fade_remap(len(y), segs[-1]["dur"], -12.0, fade_db)
            fo, _ = forward_full(pre2, segs, geom, cap, 0.90, False)
            wb = word_spans("old_input", segs)
            diff = word_db(fo, *wb[1]) - word_db(fo, *wb[0])
            line.append("oldpin=%+.2f%s" % (diff, "" if diff < -6.0 else " LOST"))
            if diff >= -6.0:
                ok = False
            dd = delta_track(len(APA_Y), APA, APA_GEOM, T)
            fapa, _ = forward_full(APA_PRE * 10.0 ** (dd / 20.0), APA, APA_GEOM, cap, 0.90, False)
            ar = apa_ratio(fapa)
            line.append("apa=%.2f%s" % (ar, " FAIL" if ar <= 1.8 else ""))
            if ar <= 1.8:
                ok = False
            line.append("ALLPASS" if ok else "")
            print(" | ".join(line))

print("=== OPTION 2: coh ON x cap x prescale on F3d25/F4d10 ===")
for tname, T in [("F3d25", F3d25), ("F4d10", F4d10)]:
    for cap in (8.0, 10.0, 12.0):
        for pre in (0.95, 1.10):
            line = ["%s cap%d pre%.2f" % (tname, cap, pre)]
            ok = True
            for name in ["demo_hello", "annyeong", "yeobo"]:
                y = load_y(name)
                segs = items[name]["segs"]
                geom = work_geometry(segs)
                pre2 = d[name + "_pre"] * 10.0 ** (delta_track(len(y), segs, geom, T) / 20.0)
                f, info = forward_full(pre2, segs, geom, cap, pre, True)
                m = full_gates(f, name, segs, geom)
                flag = ""
                checks = abs(m["halves"]) <= 5.0 and m["trough"] >= -14.0 and m["rms"] >= 0.095 and m["spark"] < 0.9 and m["cohviol"] == 0
                if name == "yeobo":
                    checks = checks and m["tail"] >= 0.03
                if not checks:
                    flag = " FAIL"
                    ok = False
                line.append("%s h=%+.1f t=%+.1f r=%.3f tl=%.3f sp=%.4f cl=%d cv=%d%s" % (
                    name[:2], m["halves"], m["trough"], m["rms"], m["tail"],
                    m["spark"], m["clamp"], m["cohviol"], flag))
            line.append("ALLPASS" if ok else "")
            print(" | ".join(line))
print("done grid3")
