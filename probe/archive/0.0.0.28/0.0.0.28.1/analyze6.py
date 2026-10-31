"""0.0.0.28.1 part 6: V6 = V2 + h-fric cooled -10 -> -12dB.
Tests whether moving the global max off the h-burst lets hello s1 go green.
Also reports max-sample positions and cluster s1 (report-only)."""
import re, os
import numpy as np
import importlib.util
spec = importlib.util.spec_from_file_location("a5", os.path.join(
    r"E:\01_coding\ARTicul\probe\0.0.0.28.1", "analyze5.py"))

# reuse by exec (analyze5 runs grid on import; instead replicate minimal path here)
exec(open(r"E:\01_coding\ARTicul\probe\0.0.0.28.1\analyze5.py").read().split("for vname, (D, cap_db")[0])

def make_deltas_V6():
    # V6 was floor-blocked (h -12 -> floored to -6). Redefined family:
    # V7 = HALF arms (h kept -10) + decl/2 + fin/2, floor KEPT -12.
    # V8 = V7 + h-fric base -10 -> -12 (floor -12 permits: -12+decl/2 >= -12 for u0/u6? u6: -12-3=-15 -> -12).
    D = {}
    for name, it in items.items():
        ds = []
        for s in it["segs"]:
            b = s["base"]
            if s["arm"] == "h-fric":
                nb = b  # V7: keep
            else:
                nb = b/2.0
            new = max(nb + s["decl"]/2.0 + s["fin"]/2.0, -12.0)
            ds.append(new - s["g"])
        D[name] = ds
    return D

def make_deltas_V8():
    D = {}
    for name, it in items.items():
        ds = []
        for s in it["segs"]:
            b = s["base"]
            if s["arm"] == "h-fric":
                nb = -12.0  # V8: cool h 2dB; floor -12 kept so it sticks
            else:
                nb = b/2.0
            new = max(nb + s["decl"]/2.0 + s["fin"]/2.0, -12.0)
            ds.append(new - s["g"])
        D[name] = ds
    return D

D7 = make_deltas_V6(); D8 = make_deltas_V8()
print("hello deltas V7:", [round(v,2) for v in D7["demo_hello"]])
print("hello deltas V8:", [round(v,2) for v in D8["demo_hello"]])
print("annyeong tail deltas V7:", [round(v,2) for v in D7["annyeong"][5:]])
print("annyeong u6 h V7/V8:", round(D7["annyeong"][6],2), round(D8["annyeong"][6],2))

for vname, (D, cap_db, prescale) in [
        ("V2", (make_deltas(keep_h=True), 12.0, 1.1)),
        ("V7_floor12", (D7, 12.0, 1.1)),
        ("V8_h-12_floor12", (D8, 12.0, 1.1))]:
    print("=== %s cap=%.1f pre=%.2f ===" % (vname, cap_db, prescale))
    for name in ["demo_hello", "annyeong", "yeobo", "fixed_sentence",
                 "cluster_probe", "pause_probe", "creak_probe", "gain_probe", "old_input"]:
        y = Y0[name]
        pre2 = PRE[name]*10.0**(delta_track(len(y), name, D)/20.0)
        y2, g2, G2, gdb2 = forward(pre2, cap_db, prescale)
        n = len(y2)
        amax = int(np.argmax(np.abs(y2)))
        pk = float(np.max(np.abs(y2)))
        h0 = rms(y2[:n//2]); h1 = rms(y2[n//2:])
        hd = 20*np.log10(max(h1,1e-9))-20*np.log10(max(h0,1e-9))
        tl = rms(y2[2*(n//3):])
        tr = trough(y2)
        nc = int((np.abs(y2) >= 0.985).sum())
        sp = spark(y2, name) if name in ["demo_hello", "annyeong", "yeobo"] else float("nan")
        # cluster s1 window (report-only, gate mirror on first boundary)
        cl1 = ""
        if name == "cluster_probe":
            seg = y2[1544:1544+220]
            uncl = seg[np.abs(seg) < 0.985]
            cl1 = " s1=%.4f/cl%d" % (float(np.max(np.abs(uncl))), int((np.abs(seg) >= 0.985).sum()))
        print("  %-14s rms=%.4f halves=%+.2f trough=%+.2f tail=%.4f spark=%.4f cl=%d maxgdb=%.1f maxpos=%d%s" % (
            name, rms(y2), hd, tr, tl, sp, nc, gdb2.max(), amax, cl1))
