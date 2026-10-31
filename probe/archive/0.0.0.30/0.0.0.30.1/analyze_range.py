import os, sys
import numpy as np
sys.path.insert(0, os.path.join(r"E:\01_coding\ARTicul", "probe", "0.0.0.30.1"))
from gchain import *
items = load_plan()
d = np.load(os.path.join(P, "chain.npz"))
NAMES = ["fixed_sentence", "demo_hello", "creak_probe", "gain_probe",
         "cluster_probe", "pause_probe", "annyeong", "yeobo", "old_input"]
print("=== LEVELER APPLIED RANGE (current tree, per 20ms window gdb) ===")
for name in NAMES:
    pre = d[name + "_pre"]
    _, g, G, gdb = forward_leveler(pre, 12.0, 1.10)
    lift = g * G
    print("%s gdb min=%+.2f max=%+.2f span=%.2f | lift>=4x frac=%.3f liftmax=%.2fx" % (
        name, gdb.min(), gdb.max(), gdb.max() - gdb.min(),
        (lift >= 4.0).mean(), lift.max()))
print("=== MAKEUP AT SPARK WINDOWS (current tree; gate mirror) ===")
for name in ["demo_hello", "annyeong", "yeobo"]:
    pre = d[name + "_pre"]
    _, g, G, gdb = forward_leveler(pre, 12.0, 1.10)
    segs = items[name]["segs"]
    geom = work_geometry(segs)
    nw = len(g)
    for gi in range(1, len(geom["groups"])):
        wpos = geom["starts"][gi] / WIN
        k = min(int(wpos), nw - 1)
        print("%s s%d win=%d gdb=%+.2fdB Glift=%+.2fdB" % (
            name, gi, k, gdb[k], 20 * np.log10(G)))
print("=== COHERENCE APPLIED RANGE (current tree, per-unit dB) ===")
for name in NAMES:
    y = np.frombuffer(open(os.path.join(P, name + ".wav"), "rb").read()[44:], dtype=np.int16).astype(np.float64) / 32768.0
    segs = items[name]["segs"]
    geom = work_geometry(segs)
    pre = d[name + "_pre"]
    lev, _, _, _ = forward_leveler(pre, 12.0, 1.10)
    _, cg, _ = forward_coherence(lev, segs, geom)
    print("%s coh unit-gains min=%+.2f max=%+.2f dB" % (name, 20 * np.log10(cg.min()), 20 * np.log10(cg.max())))
