"""0.0.0.28.1 part 7 FINAL: V2 confirmation (HALF table floor-6, h kept -10;
cap 12dB, prescale 1.1). Full gate table + histogram + tail budget."""
import os
exec(open(r"E:\01_coding\ARTicul\probe\0.0.0.28.1\analyze5.py").read().split("for vname, (D, cap_db")[0])

D = make_deltas(keep_h=True)
cap_db, prescale = 12.0, 1.1
print("=== FINAL V2 CONFIRMATION cap=12 pre=1.1 ===")
print("deltas:")
for name in ["fixed_sentence", "demo_hello", "creak_probe", "gain_probe", "cluster_probe",
             "pause_probe", "annyeong", "yeobo", "old_input"]:
    print("  %-14s %s" % (name, " ".join("%+.2f" % v for v in D[name])))
for name in ["fixed_sentence", "demo_hello", "creak_probe", "gain_probe", "cluster_probe",
             "pause_probe", "annyeong", "yeobo", "old_input"]:
    y = Y0[name]
    pre2 = PRE[name]*10.0**(delta_track(len(y), name, D)/20.0)
    y2, g2, G2, gdb2 = forward(pre2, cap_db, prescale)
    n = len(y2)
    pk = float(np.max(np.abs(y2)))
    h0 = rms(y2[:n//2]); h1 = rms(y2[n//2:])
    hd = 20*np.log10(max(h1,1e-9))-20*np.log10(max(h0,1e-9))
    tl = rms(y2[2*(n//3):])
    tr = trough(y2)
    nc = int((np.abs(y2) >= 0.985).sum())
    sp = spark(y2, name) if name in ["demo_hello", "annyeong", "yeobo"] else float("nan")
    extra = ""
    if name == "demo_hello":
        b = word_bounds(name, [2, 3])
        extra = " bal=%+.2f" % (word_db(y2, *b[1]) - word_db(y2, *b[0]))
    if name == "old_input":
        b = word_bounds(name, [2, 3])
        bal = word_db(y2, *b[1]) - word_db(y2, *b[0])
        extra = " viol=%+.2f" % bal
    print("  %-14s rms=%.4f(%s) halves=%+.2f(%s) trough=%+.2f(%s) tail=%.4f(%s) spark=%.4f cl=%d maxgdb=%.1f meangdb=%.1f%s" % (
        name, rms(y2), "P" if rms(y2) >= 0.10 else "f",
        hd, "P" if abs(hd) <= 5.0 else "f",
        tr, "P" if tr >= -14.0 else "f",
        tl, "P" if tl >= 0.03 else "f",
        sp, nc, gdb2.max(), gdb2.mean(), extra))
    # tail-budget: windows with gdb >= 11 (within 1dB of cap)
    nb = int((gdb2 >= 11.0).sum())
    print("      G=%.4f win_cap11plus=%d/%d frac_lift>=8x=%.3f" % (
        G2, nb, len(gdb2), (((10.0**(gdb2/20.0))*G2) >= 8.0).mean()))

print("=== PLANNED-GAIN HISTOGRAM (production table, 45 segs) ===")
allg = [s["g"] for it in items.values() for s in it["segs"]]
bins = [(-99, -12.0, "at floor -12"), (-12.0, -9.0, "(-12,-9]"), (-9.0, -6.0, "(-9,-6]"),
        (-6.0, -3.0, "(-6,-3]"), (-3.0, -1.0, "(-3,-1]"), (-1.0, 99, ">-1 (near 0dB)")]
for lo, hi, tag in bins:
    c = sum(1 for v in allg if (v <= lo+1e-9 if hi == -12.0 else lo < v <= hi+1e-9))
    print("  %-16s n=%d" % (tag, c))
print("  floor frac=%.3f near0 frac=%.3f" % (
    sum(1 for v in allg if v <= -11.999)/len(allg), sum(1 for v in allg if v >= -1.0)/len(allg)))
