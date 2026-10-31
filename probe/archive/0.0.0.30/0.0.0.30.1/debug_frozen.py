import os, sys, wave
import numpy as np
sys.path.insert(0, os.path.join(r"E:\01_coding\ARTicul", "probe", "0.0.0.30.1"))
from gchain import *
items = load_plan()
d = np.load(os.path.join(P, "chain.npz"))
for name in ["gain_probe", "demo_hello", "annyeong", "yeobo", "creak_probe"]:
    w = wave.open(os.path.join(P, name + ".wav"), "rb")
    y = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768.0
    pre = d[name + "_pre"]
    segs = items[name]["segs"]; geom = work_geometry(segs)
    f, info = forward_full(pre, segs, geom)
    fr = (np.abs(f) >= 0.985) | (np.abs(y) >= 0.985)
    idx = np.where(fr)[0]
    print("%s frozen_n=%d globalymax=%.4f globalfmax=%.4f" % (name, len(idx), float(np.max(np.abs(y))), float(np.max(np.abs(f)))))
    for s in idx[:12]:
        a = max(0, s - 2); b = min(len(y), s + 3)
        print("   s=%d y=%s f=%s starts=%s" % (s,
            np.array2string(y[a:b], precision=4, separator=","),
            np.array2string(f[a:b], precision=4, separator=","),
            [t for t in geom["starts"] if abs(t - s) <= 3]))
