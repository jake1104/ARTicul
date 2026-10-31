import wave, struct
import numpy as np
SR = 22050
WIN = int(0.010 * SR)
CLAMP = 0.985
BOUND_TOL = int(0.010 * SR)
INSET = int(round(0.030 * SR))

def load(p):
    w = wave.open(p, "rb")
    n = w.getnframes()
    return np.array(struct.unpack("<%dh" % n, w.readframes(n)), dtype=np.float64) / 32767.0

DEMOS = {
    "hello": ("probe/0.0.0.29.2/census-hello.wav", [1720, 1962, 1544, 5094],
              [0, 176, 176, 176]),
    "annyeong": ("probe/0.0.0.29.2/census-annyeong.wav",
                 [3947, 1147, 992, 904, 1940, 992, 1147, 2602, 1279, 1455, 904, 2073],
                 [0, 176, 176, 176, 176, 176, 176, 176, 176, 176, 176, 176]),
    "yeobo": ("probe/0.0.0.29.2/census-yeobo.wav",
              [948, 2867, 904, 2271, 1301, 2844, 904, 3859],
              [0, 176, 176, 176, 176, 176, 176, 176]),
}

for name, (path, lens, fades) in DEMOS.items():
    x = load(path)
    starts = []
    acc = 0
    for k, ln in enumerate(lens):
        starts.append(acc)
        acc += ln if k + 1 == len(lens) else ln - fades[k + 1]
    assert acc == len(x), (name, acc, len(x))
    spans = list(zip(starts, [s + ln for s, ln in zip(starts, lens)]))
    idx = np.where(np.abs(x) >= CLAMP)[0]
    print("== %s len=%d clamped_total=%d rate=%.2f_per_s" % (
        name, len(x), len(idx), len(idx) / (len(x) / SR)))
    per = {}
    for j in idx:
        g = max([i for i, (s0, s1) in enumerate(spans) if s0 <= j < s1])
        per[g] = per.get(g, 0) + 1
    print("clamped per work-unit %s" % per)
    nw = len(x) // WIN
    rows = []
    for k in range(nw):
        seg = x[k * WIN:(k + 1) * WIN]
        a = np.abs(seg)
        au = a[a < CLAMP]
        rows.append(((k + 0.5) * WIN, float(au.max()) if au.size else 0.0))
    rows.sort(key=lambda r: -r[1])
    print("top10 unclamped-per-10ms-window center_ms value near_boundary")
    for c, v in rows[:10]:
        near = any(abs(c - s) <= BOUND_TOL for s in starts)
        print("  %.1f %.4f %s" % (c * 1000.0 / SR, v, "BOUNDARY" if near else "-"))
    print("interior control same loud segments mid-segment windows >=30ms from any boundary")
    for gi in range(len(lens)):
        s0, s1 = spans[gi]
        lo, hi = s0 + INSET, s1 - INSET
        if hi - lo < WIN:
            print("  work%d span too short for interior" % gi)
            continue
        best = 0.0
        p = lo
        while p + WIN <= hi:
            a = np.abs(x[p:p + WIN])
            au = a[a < CLAMP]
            if au.size and au.max() > best:
                best = float(au.max())
            p += WIN
        print("  work%d interior_unclamped_max=%.4f %s" % (
            gi, best, "HOT" if best >= 0.9 else "ok"))
