import os, sys
import numpy as np
sys.path.insert(0, os.path.join(r"E:\01_coding\ARTicul", "probe", "0.0.0.30.1"))
from gchain import *
from analyze_flat import (new_gain, items, NAMES)
from analyze_flat2 import TABLES2

for tname in ["V2", "F3d25", "F4d10"]:
    T = {"V2": dict(__import__("analyze_flat").TABLES["V2"]), "F3d25": TABLES2["F3d25"], "F4d10": TABLES2["F4d10"]}[tname]
    print("== %s max adjacent planned steps ==" % tname)
    for name in NAMES + ["demo_hello", "annyeong", "yeobo"]:
        if name in NAMES:
            pass
        segs = items[name]["segs"] if name in items else None
        if segs is None:
            continue
        gs = [new_gain(s, s["i"], len(segs), T) for s in segs]
        for k in range(len(gs) - 1):
            d = gs[k + 1] - gs[k]
            if abs(d) >= 4.0:
                print("  %s u%d->u%d %+.2f" % (name, k, k + 1, d))

print("== gain.rs re-derivation map (F3d25; unit idx/total as in tests) ==")
T = TABLES2["F3d25"]
cases = [
    ("stressed-vowel a 0/3", "stressed-vowel", 0, 3, 0.0),
    ("unstressed-vowel a 0/3", "unstressed-vowel", 0, 3, -1.25),
    ("nasal m 0/3", "nasal", 0, 3, -3.5),
    ("sonorant l 0/3", "approximant", 0, 3, -3.0),
    ("sibilant s 0/3", "sibilant", 0, 3, -2.0),
    ("weak f 0/3", "weak-fric", 0, 3, -6.0),
    ("voiced-sib z 0/3", "voiced-sibilant+voff", 0, 3, -6.0),
    ("voiced-weak v 0/3", "voiced-weak-fric+voff", 0, 3, -6.0),
    ("plosive t 0/2", "other-stop", 0, 2, 0.0),
    ("aspirated h_h 0/3", "asp", 0, 3, -1.5),
    ("decl a-uns 2/10", "unstressed-vowel", 2, 10, -1.25 - 0.5),
    ("declcap a-uns 20/30", "unstressed-vowel", 20, 30, -1.25 - 3.0),
    ("final-cons t 4/5", "other-stop", 4, 5, 0.0 - 1.0 - 2.0),
    ("final-vowel a 4/5", "unstressed-vowel", 4, 5, -1.25 - 1.0),
]
for label, arm, idx, total, expect in cases:
    print("  %-24s expect %+.2f" % (label, max(expect, -T["floor"])))
