import os, sys, wave
import numpy as np
sys.path.insert(0, os.path.join(r"E:\01_coding\ARTicul", "probe", "0.0.0.30.1"))
from gchain import *

items = load_plan()
name = sys.argv[1] if len(sys.argv) > 1 else "demo_hello"
w = wave.open(os.path.join(P, name + ".wav"), "rb")
y = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768.0
segs = items[name]["segs"]
geom = work_geometry(segs)
pre = y.copy()
for it in range(12):
    f, info = forward_full(pre, segs, geom)
    print("it=%d maxpre=%.3e maxf=%.4f G=%.3e Gc=%.3e cresid=%.3e" % (
        it, float(np.max(np.abs(pre))), float(np.max(np.abs(f))), info["G"],
        info.get("cinfo", {}).get("Gc", float("nan")),
        float(np.max(np.abs(f - y)))))
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(np.abs(f) > 1e-9, y / f, 1.0)
    ratio = np.clip(ratio, 0.25, 4.0)
    ratio[np.abs(y) >= 0.985] = 1.0
    pre = pre * np.power(np.maximum(ratio, 1e-12), 0.7)
    pre = pre * (rms(y) / max(rms(pre), 1e-12))
