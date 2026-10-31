"""0.0.0.30.1 part 2: leveler makeup + clamp census + current-tree gate metrics.
Inverts the full chain (leveler + coherence residue) per item, reports makeup
distribution, clamp engagement, spark windows, and 28.3-vs-current deltas."""
import os, sys, hashlib, wave
import numpy as np
sys.path.insert(0, os.path.join(r"E:\01_coding\ARTicul", "probe", "0.0.0.30.1"))
from gchain import *

items = load_plan()
NAMES = ["fixed_sentence", "demo_hello", "creak_probe", "gain_probe",
         "cluster_probe", "pause_probe", "annyeong", "yeobo", "old_input"]

def load_wav(name):
    path = os.path.join(P, name + ".wav")
    raw = open(path, "rb").read()
    w = wave.open(path, "rb")
    n = w.getnframes()
    return raw, n, np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float64) / 32768.0

def load_f32(name):
    return np.fromfile(os.path.join(P, name + ".f32"), dtype=np.float32).astype(np.float64)

print("=== WAV vs F32 CROSS-CHECK (quantization bound) ===")
for name in NAMES:
    _, _, y = load_wav(name)
    f = load_f32(name)
    d = float(np.max(np.abs(y - f[:len(y)])))
    print("%s max|wav-f32|=%.2e %s" % (name, d, "OK" if d < 5e-5 else "LARGE"))

print("=== 28.3-vs-CURRENT DELTA (demos on disk are 28.3) ===")
for a, b in [("demo_hello", "demo/hello.wav"), ("annyeong", "demo/annyeonghaseyo.wav"),
             ("yeobo", "demo/yeoboseyo.wav")]:
    _, _, y = load_wav(a)
    rb = open(os.path.join(ROOT, b), "rb").read()
    w = wave.open(os.path.join(ROOT, b), "rb")
    ref = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768.0
    print("%s: rms %.4f -> %.4f (%+.2fdB), peak %.4f -> %.4f, maxabs-diff %.4f" % (
        a, rms(ref), rms(y), 20 * np.log10(max(rms(y), 1e-9) / max(rms(ref), 1e-9)),
        float(np.max(np.abs(ref))), float(np.max(np.abs(y))),
        float(np.max(np.abs(y - ref)))))

print("=== FULL-CHAIN INVERSION (leveler + coherence) ===")
REC = {}
for name in NAMES:
    _, n, y = load_wav(name)
    segs = items[name]["segs"]
    geom = work_geometry(segs)
    pre, info, resid = invert_full(y, segs, geom)
    fwd, _ = forward_full(pre, segs, geom)
    fwdres = float(np.max(np.abs(fwd[np.abs(y) < 0.985] - y[np.abs(y) < 0.985])))
    REC[name] = (pre, info, y)
    g, G, gdb = info["g"], info["G"], info["gdb"]
    lift = g * G
    print("%s inw=%d G=%.4f(%+.2fdB) resid=%.2e fwdres=%.2e" % (
        name, len(g), G, 20 * np.log10(G), resid, fwdres))
    print("   makeup dB: max=%6.2f mean=%6.2f p50=%6.2f frac>=12(cap)=%.3f" % (
        gdb.max(), gdb.mean(), np.median(gdb), (gdb >= 11.99).mean()))
    print("   makeup lin: max=%5.2fx mean=%5.2fx | TOTAL lift max=%5.2fx mean=%5.2fx frac>=4x=%.3f" % (
        g.max(), g.mean(), lift.max(), lift.mean(), (lift >= 4.0).mean()))
    cinfo = info.get("cinfo", {})
    if not cinfo.get("idle"):
        cg = info["cgains"]
        print("   coherence: target=%.4f range %+.2f..%+.2fdB nclipped=%d Gc=%.4f" % (
            cinfo["target"], 20 * np.log10(cg.min()), 20 * np.log10(cg.max()),
            sum(1 for v in cg for _ in [0] if abs(20 * np.log10(v)) >= 5.999), cinfo["Gc"]))
    else:
        print("   coherence: IDLE (no normalizable units)")
np.savez(os.path.join(P, "chain.npz"),
         **{n + "_pre": REC[n][0] for n in NAMES},
         **{n + "_G": np.array([REC[n][1]["G"]]) for n in NAMES})

print("=== CLAMP CENSUS (global |x|>=0.985) + SPARK WINDOWS (gate mirror) ===")
for name in ["demo_hello", "annyeong", "yeobo", "fixed_sentence", "cluster_probe",
             "pause_probe", "creak_probe", "gain_probe", "old_input"]:
    _, n, y = load_wav(name)
    segs = items[name]["segs"]
    geom = work_geometry(segs)
    nc = int((np.abs(y) >= 0.985).sum())
    sp = spark_windows(y, geom)
    inl = [v for _, _, v, _ in sp]
    print("%s n=%d clamp_n=%d worst_win=%.4f mean_win=%.4f" % (name, n, nc, max(inl) if inl else 0.0, float(np.mean(inl)) if inl else 0.0))
    for gi, s0, pk, cl in sp:
        flag = "SPARK" if pk >= 0.9 else "ok"
        print("   start%d pos=%d unclamped=%.4f clamped=%d %s" % (gi, s0, pk, cl, flag))

print("=== CURRENT-TREE GATE METRICS (28.3 baselines in parens) ===")
BASE28 = {
    "demo_hello": (-3.16, -2.76, 0.1831), "annyeong": (2.99, -12.31, 0.1037),
    "yeobo": (-3.11, -10.40, 0.1146),
}
for name in ["demo_hello", "annyeong", "yeobo"]:
    _, n, y = load_wav(name)
    h0, h1 = rms(y[:n // 2]), rms(y[n // 2:])
    halves = 20 * np.log10(max(h1, 1e-9)) - 20 * np.log10(max(h0, 1e-9))
    tr = trough_max_db(y)
    g = rms(y)
    tail = rms(y[2 * (n // 3):])
    b = BASE28[name]
    print("%s halves=%+.2f (28.3 %+.2f) trough=%+.2f (%.2f) rms=%.4f (%.4f) tail=%.4f" % (
        name, halves, b[0], tr, b[1], g, b[2], tail))
print("done level")
