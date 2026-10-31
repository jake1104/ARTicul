import os
import wave
import hashlib

import numpy as np

D = "probe/0.0.0.22.4/spot"
SR = 22050

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
    print("%-14s samples=%5d rms=%7.2fdBFS centroid=%8.1fHz sha=%s"
          % (name, n, rms, cent, hashlib.sha256(raw).hexdigest()[:16]))

demo_spot = open(os.path.join(D, "demo_hello.wav"), "rb").read()
demo_live = open("demo/hello.wav", "rb").read()
print("demo_hello spot-vs-live byte-identical:", demo_spot == demo_live)
