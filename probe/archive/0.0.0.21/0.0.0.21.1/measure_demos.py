import wave

import numpy as np


def analyze(path):
    with wave.open(path) as w:
        n = w.getnframes()
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(float) / 32768.0
    peak = float(np.max(np.abs(x)))
    rms = float(np.sqrt(np.mean(x ** 2)))
    h = len(x) // 2
    r1 = float(np.sqrt(np.mean(x[:h] ** 2)))
    r2 = float(np.sqrt(np.mean(x[h:] ** 2)))
    halves = 20 * np.log10(r2 / max(r1, 1e-9))
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    freqs = np.fft.rfftfreq(len(x), 1.0 / sr)
    centroid = float(np.sum(freqs * spec) / max(np.sum(spec), 1e-12))
    print("%s: frames=%d sr=%d dur=%.3fs peak=%.4f rms=%.4f halves=%+.2fdB centroid=%.1fHz"
          % (path, n, sr, n / sr, peak, rms, halves, centroid))


analyze("demo/annyeonghaseyo.wav")
analyze("demo/gamsahamnida.wav")
