import wave, struct
import numpy as np
SR = 22050
WIN = int(0.010 * SR)
CTX = int(0.015 * SR)
LAG_LO = int(round(SR / 300.0))
LAG_HI = int(round(SR / 80.0))
CLAMP = 0.985

def load(p):
    w = wave.open(p, "rb")
    n = w.getnframes()
    return np.array(struct.unpack("<%dh" % n, w.readframes(n)), dtype=np.float64) / 32767.0

def win_metrics(x, s):
    seg = x[s:s + WIN]
    a = np.abs(seg)
    d = int(np.argmax(a))
    peak = float(a[d])
    au = a[a < CLAMP]
    uncl = float(au.max()) if au.size else 0.0
    clamped = int((a >= CLAMP).sum())
    return d, peak, uncl, clamped

def harm(x, p):
    lo = max(0, p - CTX)
    hi = min(len(x), p + CTX + 1)
    c = x[lo:hi] - x[lo:hi].mean()
    denom = float((c ** 2).sum())
    if denom <= 0:
        return 0.0
    best = 0.0
    for lag in range(LAG_LO, LAG_HI + 1):
        if lag >= len(c):
            break
        v = float((c[:len(c) - lag] * c[lag:]).sum()) / denom
        if v > best:
            best = v
    return best

CASES = [
    ("annyeong", "demo/annyeonghaseyo.wav", "probe/0.0.0.29.2/annyeong.wav", 15373),
    ("yeobo", "demo/yeoboseyo.wav", "probe/0.0.0.29.2/yeobo.wav", 10807),
]
for name, pre_path, post_path, s in CASES:
    pre = load(pre_path)
    post = load(post_path)
    assert len(pre) == len(post), (name, len(pre), len(post))
    for tag, x in (("pre", pre), ("post", post)):
        d, peak, uncl, clamped = win_metrics(x, s)
        h = harm(x, s + d)
        print("%s %s win=[%d,%d) d=%d (%.2fms) peak=%.4f unclamped=%.4f clamped=%d harm=%.3f" % (
            name, tag, s, s + WIN, d, d * 1000.0 / SR, peak, uncl, clamped, h))
    d0, _, u0, _ = win_metrics(pre, s)
    d1, _, u1, _ = win_metrics(post, s)
    print("%s pre/post unclamped %.4f -> %.4f (%+.2fdB) d %d -> %d harm %.3f -> %.3f" % (
        name, u0, u1, 20 * np.log10(max(u1, 1e-9) / max(u0, 1e-9)),
        d0, d1, harm(pre, s + d0), harm(post, s + d1)))
