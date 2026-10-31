import os
import wave
import hashlib

import numpy as np

D = "probe/0.0.0.20.3/spot"
SR = 22050
N_FFT = 8192


def notch_depth(x, t0, t1):
    seg = x[int(t0 * SR):int(t1 * SR)]
    W = np.hanning(len(seg))
    S = np.abs(np.fft.rfft(seg * W, n=N_FFT)) ** 2
    freqs = np.fft.rfftfreq(N_FFT, 1.0 / SR)

    def med(lo, hi):
        m = (freqs >= lo) & (freqs < hi)
        return float(10.0 * np.log10(np.median(S[m])))

    edge = med(2000.0, 2300.0)
    core = med(2470.0, 2530.0)
    return edge - core


for name in ["fixed_sentence", "demo_hello", "creak_probe", "gain_probe", "cluster_probe", "pause_probe"]:
    p = os.path.join(D, name + ".wav")
    raw = open(p, "rb").read()
    with wave.open(p, "rb") as w:
        n = w.getnframes()
        data = w.readframes(n)
    x = np.frombuffer(data, dtype=np.int16).astype(np.float64) / 32767.0
    rms = 20 * np.log10(max(np.sqrt(float((x * x).mean())), 1e-9))
    m = len(x)
    win = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(m) / m)
    spec = np.abs(np.fft.rfft(x * win))
    freqs = np.fft.rfftfreq(m, 1.0 / SR)
    cent = float((freqs * spec).sum() / max(spec.sum(), 1e-12))
    dur = n / SR
    c0, c1 = dur / 2 - 0.020, dur / 2 + 0.020
    nd = notch_depth(x, c0, c1)
    print("%-14s samples=%5d rms=%7.2fdBFS centroid=%8.1fHz notch_mid40ms=%+.2fdB sha=%s"
          % (name, n, rms, cent, nd, hashlib.sha256(raw).hexdigest()[:16]))

demo_spot = open(os.path.join(D, "demo_hello.wav"), "rb").read()
demo_live = open("demo/hello.wav", "rb").read()
print("demo_hello spot-vs-live byte-identical:", demo_spot == demo_live)
