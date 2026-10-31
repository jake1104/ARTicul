import os
import wave

import numpy as np
import librosa

D = "probe/0.0.0.19.6/spot"
SR = 22050
rows = []
for name in ["fixed_sentence", "demo_hello", "creak_probe", "gain_probe", "cluster_probe", "pause_probe"]:
    p = os.path.join(D, name + ".wav")
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
    f0, voiced, _ = librosa.pyin(x, fmin=50.0, fmax=500.0, sr=SR, frame_length=1024, hop_length=256)
    vf = float(np.mean(voiced)) if len(voiced) else 0.0
    fr, hop = 1024, 256
    ac_v = 0
    ac_n = 0
    for s in range(0, len(x) - fr, hop):
        seg = x[s:s + fr] - x[s:s + fr].mean()
        e = float(seg @ seg)
        ac_n += 1
        if e < 1e-8:
            continue
        lo, hi = SR // 500, min(len(seg) - 1, SR // 50)
        pk = max(float(seg[:len(seg) - l] @ seg[l:]) / e for l in range(lo, hi + 1))
        if pk > 0.5:
            ac_v += 1
    acf = ac_v / max(ac_n, 1)
    rows.append((name, n, rms, cent, vf))
    print("%-14s samples=%5d rms=%7.2fdBFS centroid=%8.1fHz voiced_pyin=%.3f voiced_ac=%.3f"
          % (name, n, rms, cent, vf, acf))
