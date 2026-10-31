import wave
import numpy as np

SR = 22050


def load(path):
    with wave.open(path, "rb") as w:
        n = w.getnframes()
        data = w.readframes(n)
    x = np.frombuffer(data, dtype=np.int16).astype(np.float64) / 32767.0
    return n, x


def autocorr_f0_peak(seg, fmin=60.0, fmax=300.0):
    x = seg - seg.mean()
    e0 = float((x * x).sum())
    if e0 <= 1e-12:
        return float("nan"), 0.0
    lo = int(round(SR / fmax))
    hi = int(round(SR / fmin))
    best_lag, best_v = 0, -1.0
    for lag in range(lo, min(hi, len(x) - 1) + 1):
        v = float((x[:len(x) - lag] * x[lag:]).sum()) / e0
        if v > best_v:
            best_v, best_lag = v, lag
    if best_lag == 0:
        return float("nan"), 0.0
    return SR / best_lag, best_v


for path in ["probe/0.0.0.35.1/solo_a_double.wav", "probe/0.0.0.35.1/solo_a_stressed.wav"]:
    n, x = load(path)
    print("== %s n=%d" % (path, n))
    win, hop = int(0.020 * SR), int(0.020 * SR)
    for s in range(0, n - win, hop):
        seg = x[s:s + win]
        rms = float(np.sqrt((seg * seg).mean()))
        f, pk = autocorr_f0_peak(seg)
        print("  t=%6.1fms rms=%.4f f0=%7.2f peak=%.3f" % (s / SR * 1000.0, rms, f, pk))
