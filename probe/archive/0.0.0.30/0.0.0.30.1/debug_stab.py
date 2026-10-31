import os, sys, wave
import numpy as np
sys.path.insert(0, os.path.join(r"E:\01_coding\ARTicul", "probe", "0.0.0.30.1"))
from gchain import *
items = load_plan()
for name in ["demo_hello", "annyeong", "yeobo", "gain_probe"]:
    w = wave.open(os.path.join(P, name + ".wav"), "rb")
    y = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768.0
    segs = items[name]["segs"]; geom = work_geometry(segs)
    for iters in (150, 250):
        pre, info, resid = invert_full(y, segs, geom, iters=iters)
        g = info["g"]
        print("%s it=%d G=%.4f gdbmax=%.2f gdbmean=%.2f resid=%.2e" % (
            name, iters, info["G"], info["gdb"].max(), info["gdb"].mean(), resid))
