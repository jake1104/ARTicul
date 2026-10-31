import wave
import numpy as np
import hashlib

p = "probe/0.0.0.19.2/hello-check.wav"
raw = open(p, "rb").read()
print("bytes", len(raw), "sha256", hashlib.sha256(raw).hexdigest())

with wave.open(p, "rb") as w:
    sr = w.getframerate()
    nframes = w.getnframes()
    data = w.readframes(nframes)
x = np.frombuffer(data, dtype=np.int16).astype(np.float64) / 32767.0
print("samples", len(x), "sr", sr)

def rms_db(v):
    return 20 * np.log10(max(np.sqrt(float((v * v).mean())), 1e-9))

n = len(x)
print("halves db0 %.2f db1 %.2f diff %+.2f" % (rms_db(x[: n // 2]), rms_db(x[n // 2 :]), rms_db(x[n // 2 :]) - rms_db(x[: n // 2])))

o_start = 1720 + 1962 + 1103 - 3 * 176
start = o_start + 176 + 110
span = x[start:]
nw = 6
wlen = len(span) // nw
f2s = []
for k in range(nw):
    s = span[k * wlen:(k + 1) * wlen]
    m = len(s)
    w = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(m) / m)
    best_f, best_p = 0.0, -1.0
    for b in range(int(np.ceil(700 * m / sr)), int(1500 * m / sr) + 1):
        if b > m // 2:
            break
        ang = 2 * np.pi * b * np.arange(m) / m
        re = float((s * w * np.cos(ang)).sum())
        im = float((s * w * np.sin(ang)).sum())
        pp = re * re + im * im
        if pp > best_p:
            best_p, best_f = pp, b * sr / m
    f2s.append(best_f)
print("F2 trajectory", [round(v, 1) for v in f2s])
print("F2 rise overall", round(f2s[-1] - f2s[0], 1))

def ac_peak(seg, fmin=60, fmax=300):
    v = seg - seg.mean()
    e0 = float(v @ v)
    lo = max(1, sr // fmax)
    hi = min(len(v) - 1, sr // fmin)
    return max(float(v[: len(v) - lag] @ v[lag:]) / e0 for lag in range(lo, hi + 1))

tail = x[len(x) - int(0.080 * sr):]
print("final-80ms autocorr peak", round(ac_peak(tail), 4))
