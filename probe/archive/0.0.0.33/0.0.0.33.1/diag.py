# Diagnostic spectra for task 0.0.0.33.1: top local-max peaks per nucleus
# interior + periodicity (voicing) test for h units.
import math
import struct
import wave

import numpy as np

SR = 22050
EDGE = int(0.010 * SR)
FWIN = int(0.020 * SR)
HOP = FWIN // 2
NFFT = 4096

# (label, unitname, s0, s1) spans from measure.txt output
UNITS = [
    ("hello", "E-u1", 1544, 3506),
    ("hello", "oU-u3", 4698, 9792),
    ("annyeong", "a-u0", 0, 3947),
    ("annyeong", "V-u4", 6286, 8226),
    ("annyeong", "h-u6", 8866, 10013),
    ("annyeong", "a-u7", 9837, 12439),
    ("annyeong", "e-u9", 13366, 14821),
    ("annyeong", "o-u11", 15373, 17446),
    ("yeobo", "V-u1", 772, 3639),
    ("yeobo", "o-u3", 4191, 6462),
    ("yeobo", "e-u5", 7411, 10255),
    ("yeobo", "o-u7", 10807, 14666),
    ("yeobo", "h-none", 0, 0),
]


def load_wav(path):
    with wave.open(path, "rb") as w:
        n = w.getnframes()
        raw = w.readframes(n)
    return np.array(struct.unpack("<%dh" % n, raw), dtype=np.float64) / 32767.0


def avg_power(interior):
    win = np.hanning(FWIN)
    specs = []
    p = 0
    while p + FWIN <= len(interior):
        fr = interior[p:p + FWIN] * win
        specs.append(np.abs(np.fft.rfft(fr, NFFT)) ** 2)
        p += HOP
    return np.mean(np.stack(specs), axis=0)


def top_peaks(power, n=10):
    freqs = np.fft.rfftfreq(NFFT, 1.0 / SR)
    mask = (freqs >= 150) & (freqs <= 4500)
    idx = np.where(mask)[0]
    p = power[idx]
    pmax = p.max()
    cands = []
    for k in range(1, len(p) - 1):
        if p[k] >= p[k - 1] and p[k] >= p[k + 1]:
            cands.append((freqs[idx[k]], 10 * math.log10(p[k] / pmax)))
    cands.sort(key=lambda t: -t[1])
    # greedy min-separation 120 Hz
    picked = []
    for f, db in cands:
        if all(abs(f - q[0]) > 120 for q in picked):
            picked.append((f, db))
        if len(picked) == n:
            break
    return picked


def periodicity(interior):
    # normalized autocorrelation max over lags for 60..300 Hz
    x = interior - interior.mean()
    denom = float(np.dot(x, x))
    if denom <= 0:
        return 0.0
    best = 0.0
    for lag in range(int(SR / 300), int(SR / 60)):
        v = float(np.dot(x[:len(x) - lag], x[lag:])) / denom
        best = max(best, v)
    return best


def main():
    wavs = {
        "hello": load_wav("probe/0.0.0.33.1/hello.wav"),
        "annyeong": load_wav("probe/0.0.0.33.1/annyeong.wav"),
        "yeobo": load_wav("probe/0.0.0.33.1/yeobo.wav"),
    }
    lines = []
    for label, uname, s0, s1 in UNITS:
        if s1 <= s0:
            continue
        x = wavs[label]
        inter = x[s0 + EDGE:s1 - EDGE]
        pk = top_peaks(avg_power(inter))
        per = periodicity(inter)
        lines.append("%s %s interior_n=%d periodic=%.2f" % (label, uname,
                                                           len(inter), per))
        for f, db in pk:
            lines.append("    peak %6.0fHz %+.1fdB" % (f, db))
    text = "\n".join(lines) + "\n"
    with open("probe/0.0.0.33.1/diag.txt", "w", encoding="utf-8") as f:
        f.write(text)
    print(text.encode("ascii", errors="replace").decode("ascii"))
    print("wrote probe/0.0.0.33.1/diag.txt")


if __name__ == "__main__":
    main()
