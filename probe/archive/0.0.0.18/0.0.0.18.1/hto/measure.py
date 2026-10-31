import wave, numpy as np

def load(p):
    w = wave.open(p)
    sr = w.getframerate()
    n = w.getnframes()
    raw = w.readframes(n)
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
    return sr, n, x

def stats(name, sr, n, x):
    peak = float(np.max(np.abs(x)))
    rms = float(np.sqrt(np.mean(x ** 2)))
    zcr = float(np.mean(np.abs(np.diff(np.sign(x)))) / 2.0)
    X = np.abs(np.fft.rfft(x)) ** 2
    f = np.fft.rfftfreq(n, 1.0 / sr)
    cent = float(np.sum(f * X) / (np.sum(X) + 1e-12))
    tot = float(np.sum(X) + 1e-12)
    b1 = float(np.sum(X[f < 300]) / tot)
    b2 = float(np.sum(X[(f >= 300) & (f <= 3400)]) / tot)
    b3 = float(np.sum(X[f > 4000]) / tot)
    return peak, rms, zcr, cent, b1, b2, b3

def f0_autocorr(sr, x):
    x = x - np.mean(x)
    denom = np.dot(x, x)
    if denom < 1e-12:
        return None, 0.0
    lo = int(sr / 500)
    hi = int(sr / 50)
    best_lag, best_val = 0, -1.0
    vals = {}
    for lag in range(lo, hi + 1):
        v = float(np.dot(x[:len(x) - lag], x[lag:]) / denom)
        vals[lag] = v
        if v > best_val:
            best_val, best_lag = v, lag
    f0 = sr / best_lag
    return f0, best_val

rows = []
for name, p in [("vowel-a", "probe/0.0.0.18.1/hto/vowel-a.wav"),
                ("fric-s", "probe/0.0.0.18.1/hto/fric-s.wav")]:
    sr, n, x = load(p)
    peak, rms, zcr, cent, b1, b2, b3 = stats(name, sr, n, x)
    rows.append((name, sr, n, peak, rms, zcr, cent, b1, b2, b3))

sr, n, x = load("probe/0.0.0.18.1/hto/vowel-a.wav")
f0, ac = f0_autocorr(sr, x)

lines = []
lines.append("file frames peak rms zcr centroid band0-300 band300-3400 band4k+")
for name, s, nn, peak, rms, zcr, cent, b1, b2, b3 in rows:
    lines.append(f"{name} {nn} {peak:.4f} {rms:.4f} {zcr:.4f} {cent:.1f} {b1:.3f} {b2:.3f} {b3:.3f}")
lines.append(f"vowel-a autocorr F0 {f0:.1f} Hz peak {ac:.3f} (lag search 50-500 Hz)")
text = "\n".join(lines) + "\n"
print(text)
with open("probe/0.0.0.18.1/hto/hto.txt", "w") as fh:
    fh.write(text)
