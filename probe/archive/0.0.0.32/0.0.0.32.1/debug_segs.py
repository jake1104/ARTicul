import sys
sys.path.insert(0, r"E:\01_coding\ARTicul\probe\0.0.0.32.1")
from hfcap import (data, base, results, hf_frac_interior, EDGE, CUTOFF,
                   split_hp, simulate, notch_depth, NOTCH_WIN)
import numpy as np

# per-segment baseline hf_frac + MS, and K=1.5 simmed fracs
for name in ["hello", "annyeong", "yeobo"]:
    d = data[name]
    x = d["x"]
    _, hf = split_hp(x)
    print("== %s cutoff=%.0f" % (name, CUTOFF))
    for i in d["vset"]:
        s, e = d["ranges"][i]
        f0, eh0, et0 = hf_frac_interior(x, s + EDGE, e - EDGE)
        seg = hf[s + EDGE:e - EDGE]
        ms = float(np.mean(seg ** 2))
        y = results[1.5][name]["y"]
        f1, eh1, et1 = hf_frac_interior(y, s + EDGE, e - EDGE)
        g = results[1.5][name]["gains"][i]
        print("u%d sym=%s range=[%d,%d) int_n=%d ms=%.3e frac_base=%.5f frac_K15=%.5f g=%.3f"
              % (i, ["h", "E", "l", "o", "U"] if name == "hello" else "", s, e,
                 e - s - 2 * EDGE, ms, f0, f1, g))
# frame-mean cross-check (40ms frames / 20ms step, texture header method)
print("== frame-mean cross-check hello ==")
d = data["hello"]
x = d["x"]
FR = int(0.040 * 22050)
ST = int(0.020 * 22050)
for i in d["vset"]:
    s, e = d["ranges"][i]
    a, b = s + EDGE, e - EDGE
    fs = []
    p = a
    while p + FR <= b:
        f, _, _ = hf_frac_interior(x, p, p + FR)
        fs.append(f)
        p += ST
    fs = np.array(fs)
    print("u%d nframes=%d frame-mean=%.5f framemax/min=%.2f" % (i, len(fs), fs.mean(),
          fs.max() / fs.min() if fs.min() > 0 else float("nan")))
