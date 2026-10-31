"""0.0.0.28.1 part 8: lateral-window 8dB gate (halves_gain.rs mirror) on BASE vs V2."""
import os
exec(open(r"E:\01_coding\ARTicul\probe\0.0.0.28.1\analyze5.py").read().split("for vname, (D, cap_db")[0])

def rms_db(x):
    return 20*np.log10(max(float(np.sqrt((x*x).mean())), 1e-9))

def lateral_gap(y):
    # mirror halves_gain.rs lateral test on hello plan
    segs = items["demo_hello"]["segs"]
    vow = [s["arm"] in VOWEL_ARMS for s in segs]
    lens = [s["seglen"] for s in segs]
    fades = [0]*len(segs)
    for i in range(1, len(segs)):
        fades[i] = 1102 if (vow[i-1] and vow[i]) else 176
    starts = [0]*len(segs)
    for i in range(1, len(segs)):
        starts[i] = starts[i-1] + lens[i-1] - fades[i]
    # lateral = first approximant (u2 l); stressed vowel = first stressed vowel (u3 o)
    li, oi = 2, 3
    n = len(y)
    nf = lambda i: fades[i+1] if i+1 < len(segs) else 0
    ws = starts[li]+fades[li]+110; we = min(starts[li]+lens[li]-nf(li)-110, n)
    vs = starts[oi]+fades[oi]+110; ve = min(starts[oi]+lens[oi]-nf(oi)-110, n)
    ldb, odb = rms_db(y[ws:we]), rms_db(y[vs:ve])
    return odb-ldb, ldb, odb

D = make_deltas(keep_h=True)
for tag, y in [("BASE", Y0["demo_hello"])]:
    gap, ldb, odb = lateral_gap(y)
    print("%s lateral gap=%.2fdB (l=%.2f o=%.2f) gate<8 -> %s" % (tag, gap, ldb, odb, "PASS" if gap < 8 else "FAIL"))
pre2 = PRE["demo_hello"]*10.0**(delta_track(len(Y0["demo_hello"]), "demo_hello", D)/20.0)
y2, _, _, _ = forward(pre2, 12.0, 1.1)
gap, ldb, odb = lateral_gap(y2)
print("V2   lateral gap=%.2fdB (l=%.2f o=%.2f) gate<8 -> %s" % (gap, ldb, odb, "PASS" if gap < 8 else "FAIL"))
