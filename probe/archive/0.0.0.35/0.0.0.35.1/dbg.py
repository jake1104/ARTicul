import wave
import numpy as np

SR = 22050


def load(path):
    with wave.open(path, "rb") as w:
        n = w.getnframes()
        data = w.readframes(n)
    x = np.frombuffer(data, dtype=np.int16).astype(np.float64) / 32767.0
    return n, x


for label, path, b0, b1 in [("annyeong", "probe/0.0.0.35.1/fresh_annyeong.wav", 24216, 28693),
                            ("yeobo", "probe/0.0.0.35.1/fresh_yeobo.wav", 14312, 18877)]:
    n, x = load(path)
    print(label, "n=", n, "seg=", b0, b1)
    s = b0 + int(0.030 * SR)
    end = b1 - int(0.040 * SR)
    k = 0
    while s + int(0.030 * SR) <= end:
        seg = x[s:s + int(0.030 * SR)]
        m = 4096
        w = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(len(seg)) / len(seg))
        pw = np.abs(np.fft.rfft(seg * w, n=m)) ** 2
        fr = np.fft.rfftfreq(m, 1.0 / SR)
        for flo, fhi, nm in ((300.0, 700.0, "F1"), (600.0, 1500.0, "F2")):
            bb = (fr >= flo) & (fr <= fhi)
            c = float((fr[bb] * pw[bb]).sum() / max(pw[bb].sum(), 1e-18))
            print("  frame%d [%d,%d) %scent=%.2f maxbin=%.1f" % (
                k, s, s + int(0.030 * SR), nm, c, float(fr[bb][int(np.argmax(pw[bb]))])))
        s += int(0.030 * SR)
        k += 1
