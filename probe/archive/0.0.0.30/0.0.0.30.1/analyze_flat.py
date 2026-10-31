"""0.0.0.30.1 part 3: FLAT-table + minimal-leveler proposal simulation.
Output-domain delta method (28.1 precedent): per-segment gain deltas applied
to recovered pre-leveler signal, forward through parametrized replica
(cap/prescale/coherence on-off). Control (zero deltas) validates end-to-end.
"""
import os, sys, wave
import numpy as np
sys.path.insert(0, os.path.join(r"E:\01_coding\ARTicul", "probe", "0.0.0.30.1"))
from gchain import *

items = load_plan()
d = np.load(os.path.join(P, "chain.npz"))
NAMES = ["fixed_sentence", "demo_hello", "creak_probe", "gain_probe",
         "cluster_probe", "pause_probe", "annyeong", "yeobo", "old_input"]

V2 = dict(strV=0.0, unstrV=-1.75, sib=-2.5, approx=-3.5, nasal=-4.0, h=-10.0,
          weak=-9.0, voff=-5.0, latU=-9.0, latV=-14.0, aspmax=-1.5,
          decl=0.5, declcap=12, fin=2.0, floor=6.0)
F1 = dict(V2, decl=0.25)
F3 = dict(strV=0.0, unstrV=-1.25, sib=-2.0, approx=-3.0, nasal=-3.5, h=-8.0,
          weak=-6.0, voff=-5.0, latU=-6.0, latV=-8.0, aspmax=-1.5,
          decl=0.25, declcap=12, fin=2.0, floor=6.0)
TABLES = {"V2": V2, "F1": F1, "F3": F3}

L12 = (12.0, 1.10)
L6a = (6.0, 0.95)
L6b = (6.0, 1.00)
L8a = (8.0, 0.95)
COMBOS = [
    ("control", "V2", L12, True),
    ("A", "F1", L12, True),
    ("B", "F3", L12, True),
    ("C", "F3", L6a, True),
    ("D", "F3", L6a, False),
    ("E", "F3", L6b, False),
    ("F", "F3", L8a, False),
]


def arm_base(arm, T):
    if arm == "stressed-vowel":
        return T["strV"]
    if arm == "unstressed-vowel":
        return T["unstrV"]
    if arm == "sibilant":
        return T["sib"]
    if arm == "approximant":
        return T["approx"]
    if arm == "nasal":
        return T["nasal"]
    if arm == "h-fric":
        return T["h"]
    if arm == "weak-fric":
        return T["weak"]
    if arm == "latfric-unvoiced":
        return T["latU"]
    if arm == "latfric-voiced":
        return T["latV"]
    if arm == "other-stop":
        return 0.0
    if arm.startswith("voiced-"):
        tag = arm[len("voiced-"):].replace("+voff", "")
        b = {"sibilant": T["sib"], "weak-fric": T["weak"], "h-fric": T["h"],
             "latfric-unvoiced": T["latU"], "latfric-voiced": T["latV"]}[tag]
        return b + T["voff"]
    raise ValueError(arm)


def new_gain(seg, idx, total, T):
    b = arm_base(seg["arm"], T)
    b = max(b, T["aspmax"]) if False else b
    decl = -min(idx, T["declcap"]) * T["decl"]
    fin = -T["fin"] if (total > 0 and idx + 1 == total and seg["arm"] not in VOWEL_ARMS) else 0.0
    return max(b + decl + fin, -T["floor"])


def is_vowel_seg(seg):
    return seg["arm"] in VOWEL_ARMS


def is_fric_seg(seg):
    return seg["arm"] in ("sibilant", "weak-fric", "h-fric",
                          "latfric-unvoiced", "latfric-voiced") or "voff" in seg["arm"]


def delta_track(n, segs, geom, T):
    dd = np.zeros(n)
    deltas = [new_gain(s, s["i"], len(segs), T) - s["g"] for s in segs]
    for (s0, s1), dl in zip(geom["seg_ranges"], deltas):
        dd[max(0, s0):min(n, s1)] = dl
    # linear ramps across work-boundary fade zones between segment deltas
    groups = geom["groups"]
    for gi in range(1, len(groups)):
        prev_seg = groups[gi - 1][-1]
        cur_seg = groups[gi][0]
        f = geom["fades"][gi]
        s = geom["starts"][gi]
        d0, d1 = deltas[prev_seg], deltas[cur_seg]
        if f <= 0 or d0 == d1:
            continue
        b0, b1 = max(0, s), min(n, s + f)
        m = b1 - b0
        if m > 0:
            dd[b0:b1] = d0 + (d1 - d0) * (np.arange(m) / max(m, 1))
    # GOAT-merged interior: linear delta0->delta1 across merged span
    for g in groups:
        if len(g) == 2:
            (a0, a1), (b0, b1) = geom["seg_ranges"][g[0]], geom["seg_ranges"][g[1]]
            s0 = max(0, a0); s1 = min(n, b1)
            m = s1 - s0
            if m > 0:
                dd[s0:s1] = deltas[g[0]] + (deltas[g[1]] - deltas[g[0]]) * (np.arange(m) / max(m, 1))
    return dd


def load_y(name):
    w = wave.open(os.path.join(P, name + ".wav"), "rb")
    return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768.0


def word_spans(name, segs):
    if name in ("demo_hello", "old_input"):
        cut = 2
    else:
        return None
    lens = [s["seglen"] for s in segs]
    bounds = []
    pos = 0; wstart = 0
    bounds2 = []
    idx = 0
    words = [list(range(0, cut)), list(range(cut, len(segs)))]
    for wi, wsegs in enumerate(words):
        for k, oi in enumerate(wsegs):
            if k > 0:
                pv = is_vowel_seg(segs[wsegs[k - 1]]); cv = is_vowel_seg(segs[oi])
                pos -= min(1102 if (pv and cv) else 176, pos)
            elif wi > 0:
                pv = is_vowel_seg(segs[words[wi - 1][-1]]); cv = is_vowel_seg(segs[oi])
                pos -= min(1102 if (pv and cv) else 176, pos)
            pos += lens[oi]
        bounds2.append((wstart, pos))
        wstart = pos
    return bounds2


def word_db(x, s, e):
    s = (s + 300)
    e = max(min(e - 300, len(x)), s + 1)
    return 20 * np.log10(max(rms(x[s:e]), 1e-9))


print("=== TABLE EFFECTIVE STATS (new planned gains) ===")
for tname, T in TABLES.items():
    allg = []
    for name in NAMES:
        segs = items[name]["segs"]
        gs = [new_gain(s, s["i"], len(segs), T) for s in segs]
        allg += gs
    print("%s eff planned: min=%.2f max=%.2f spread=%.2f" % (tname, min(allg), max(allg), max(allg) - min(allg)))

RES = {}
for combo, tname, (cap, pre), coh in COMBOS:
    T = TABLES[tname]
    RES[combo] = {}
    for name in NAMES:
        y = load_y(name)
        segs = items[name]["segs"]
        geom = work_geometry(segs)
        pre_sig = d[name + "_pre"]
        dd = delta_track(len(y), segs, geom, T)
        pre2 = pre_sig * 10.0 ** (dd / 20.0)
        # NOTE: control uses zero deltas; dd is ~0 (float dust) -> validates chain
        f, info = forward_full(pre2, segs, geom, cap, pre, coh)
        info["ddmax"] = float(np.max(np.abs(dd)))
        RES[combo][name] = (f, info, geom)
    print("%s table=%s cap=%.0f pre=%.2f coh=%s max|dd|=%.3f" % (
        combo, tname, cap, pre, coh, max(v[1]["ddmax"] for v in RES[combo].values())))

print("=== CONTROL vs ENGINE (validation; dd=0 so residual = inversion+replica only) ===")
for name in NAMES:
    y = load_y(name)
    f = RES["control"][name][0]
    print("%s max|sim-eng|=%.2e rms_sim=%.4f rms_eng=%.4f" % (
        name, float(np.max(np.abs(f - y))), rms(f), rms(y)))

print("=== CONTROL SPARK vs ENGINE SPARK (bias calibration) ===")
for name in ["demo_hello", "annyeong", "yeobo"]:
    y = load_y(name)
    segs = items[name]["segs"]
    geom = work_geometry(segs)
    f = RES["control"][name][0]
    se, ss = spark_windows(y, geom), spark_windows(f, geom)
    for (gi, s0, pk, cl), (_, _, qk, ql) in zip(se, ss):
        print("%s s%d eng=%.4f sim=%.4f d=%+.4f" % (name, gi, pk, qk, qk - pk))
for combo, tname, (cap, pre), coh in COMBOS:
    print("--- %s (table %s, cap+%.0f prescale%.2f coh%s) ---" % (combo, tname, cap, pre, coh))
    for name in ["demo_hello", "annyeong", "yeobo"]:
        f, info, geom = RES[combo][name]
        n = len(f)
        h0, h1 = rms(f[:n // 2]), rms(f[n // 2:])
        halves = 20 * np.log10(max(h1, 1e-9)) - 20 * np.log10(max(h0, 1e-9))
        tr = trough_max_db(f)
        g = rms(f)
        tail = rms(f[2 * (n // 3):])
        sp = spark_windows(f, geom)
        worst = max(v for _, _, v, _ in sp)
        nc = int((np.abs(f) >= 0.985).sum())
        print("%s halves=%+.2f trough=%+.2f rms=%.4f tail=%.4f sparkmax=%.4f clamp=%d" % (
            name, halves, tr, g, tail, worst, nc))
    for name in ["demo_hello", "old_input"]:
        f, info, geom = RES[combo][name]
        segs = items[name]["segs"]
        wb = word_spans(name, segs)
        db0 = word_db(f, *wb[0]); db1 = word_db(f, *wb[1])
        print("%s balance w0=%.2f w1=%.2f diff=%+.2f %s" % (
            name, db0, db1, db1 - db0, "PIN-VIOLATES" if db1 - db0 < -6.0 else "passes"))
    # leveling eval tails + apa ratio + lateral gap + coherence RMS steps
    for name in ["gain_probe"]:
        f, info, geom = RES[combo][name]
        segs = items[name]["segs"]
        st = [0, segs[0]["seglen"] - 176, segs[0]["seglen"] - 176 + segs[1]["seglen"] - 176]
        w0 = f[500:1500]; w2 = f[st[2] + 300:st[2] + 1300]
        print("%s apa ratio=%.3f %s" % (name, rms(w0) / max(rms(w2), 1e-9),
                                        "PASS>1.8" if rms(w0) / max(rms(w2), 1e-9) > 1.8 else "FAIL"))
    f, info, geom = RES[combo]["demo_hello"]
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
    print("hello lateral gap=%.2fdB %s" % (gap, "PASS<8" if gap < 8.0 else "FAIL"))
    viol = []
    for name in ["demo_hello", "annyeong", "yeobo"]:
        f, info, geom = RES[combo][name]
        segs = items[name]["segs"]
        groups, lens_g, starts_g = geom["groups"], geom["lens"], geom["starts"]
        for gi in range(1, len(groups)):
            if any(is_fric_seg(segs[oi]) for oi in groups[gi - 1]) or any(is_fric_seg(segs[oi]) for oi in groups[gi]):
                continue
            li0 = None
            (s0, l0) = (starts_g[gi - 1], lens_g[gi - 1])
            (t0, l1) = (starts_g[gi], lens_g[gi])
            a = f[s0 + min(220, len(f)):s0 + l0 - 220]
            b = f[t0 + 220:t0 + l1 - 220]
            if len(a) < 16 or len(b) < 16:
                continue
            step = 20 * np.log10(max(rms(b), 1e-9)) - 20 * np.log10(max(rms(a), 1e-9))
            if abs(step) > 4.0:
                viol.append("%s b%d %+.2f" % (name, gi, step))
    print("coherence-RMS steps>4dB: %d %s" % (len(viol), viol if viol else "(none)"))
    for name in NAMES:
        f, info, geom = RES[combo][name]
        g = info["g"]
        print("%s makeup max=%.2f mean=%.2f capfrac=%.3f G=%+.2fdB" % (
            name, info["gdb"].max(), info["gdb"].mean(),
            (info["gdb"] >= cap - 0.01).mean(), 20 * np.log10(info["G"])))
print("done flat")
