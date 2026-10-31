import wave
import numpy as np
import sys

def load(p):
    w = wave.open(p)
    sr = w.getframerate()
    n = w.getnframes()
    raw = w.readframes(n)
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
    return sr, n, x

def spectrum(x):
    n = x.shape[0]
    X = np.abs(np.fft.rfft(x * np.hanning(n))) ** 2
    f = np.fft.rfftfreq(n, 1.0 / 22050.0)
    return f, X

def frac4k(x):
    f, X = spectrum(x)
    tot = float(np.sum(X))
    return float(np.sum(X[f >= 4000.0]) / tot)

def flatness(x):
    _, X = spectrum(x)
    X = X + 1e-12
    geo = float(np.exp(np.mean(np.log(X))))
    ari = float(np.mean(X))
    return geo / ari

for p in sys.argv[1:]:
    sr, n, x = load(p)
    print(f"{p} sr={sr} n={n} frac4k={frac4k(x):.4f} flatness={flatness(x):.4f}")
