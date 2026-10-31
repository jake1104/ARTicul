import wave
import numpy as np
import hashlib

M64 = (1 << 64) - 1


def splitmix64(x):
    x = (x + 0x9E3779B97F4A7C15) & M64
    z = x
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M64
    return z ^ (z >> 31)


def duration_variance(i):
    r = splitmix64(i ^ 0x9E3779B97F4A7C15) / float(1 << 64)
    return 1.0 + 0.12 * (r - 0.5)


def load(p):
    raw = open(p, "rb").read()
    with wave.open(p, "rb") as w:
        sr = w.getframerate()
        nframes = w.getnframes()
        data = w.readframes(nframes)
    x = np.frombuffer(data, dtype=np.int16).astype(np.float64) / 32767.0
    return raw, sr, x


def rms_db(v):
    return 20 * np.log10(max(np.sqrt(float((v * v).mean())), 1e-9))


for tag, p in [("a", "probe/0.0.0.19.3/regression-a.wav"),
               ("b", "probe/0.0.0.19.3/regression-b.wav")]:
    raw, sr, x = load(p)
    print(tag, len(raw), hashlib.sha256(raw).hexdigest(), "samples", len(x))
ra, _, xa = load("probe/0.0.0.19.3/regression-a.wav")
rb, _, xb = load("probe/0.0.0.19.3/regression-b.wav")
print("deterministic", bool(np.array_equal(xa, xb)))

raw, sr, x = load("probe/0.0.0.19.3/hello-check.wav")
print("hello bytes", len(raw), "sha256", hashlib.sha256(raw).hexdigest())
print("hello samples", len(x), "sr", sr)

h_ms = round(130.0 * 0.55 * 1.1 * duration_variance(0))
h_len = int(round(h_ms / 1000.0 * sr))
print("h duration_ms", h_ms, "h_len samples", h_len)

lo, hi = 200, h_len - 176 - 200
hw = x[lo:hi]
peak_dbfs = 20 * np.log10(max(np.abs(hw).max(), 1e-9))
print("h-window [%d:%d] peak %.2f dBFS rms %.2f dBFS" % (lo, hi, peak_dbfs, rms_db(hw)))

n = len(x)
print("halves db0 %.2f db1 %.2f diff %+.2f" % (rms_db(x[: n // 2]), rms_db(x[n // 2:]),
      rms_db(x[n // 2:]) - rms_db(x[: n // 2])))

N = 8192
seg = hw
m = len(seg)
w = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(m) / m)
spec = np.abs(np.fft.rfft(seg * w, n=N)) ** 2
sm = np.convolve(spec, np.ones(25) / 25, mode="same")
freqs = np.fft.rfftfreq(N, 1.0 / sr)
for target, tol in [(576.0, 200.0), (1624.0, 200.0)]:
    band = (freqs >= target - tol) & (freqs <= target + tol)
    idx = np.where(band)[0]
    med = np.median(sm[idx])
    best = None
    for k in idx[2:-2]:
        if sm[k] > sm[k - 1] and sm[k] > sm[k - 2] and sm[k] >= sm[k + 1] \
                and sm[k] >= sm[k + 2] and sm[k] > 3.0 * med:
            if best is None or sm[k] > sm[best]:
                best = k
    print("h-window peak near %.0f: %s" % (target,
          ("%.1f Hz" % freqs[best]) if best is not None else None))
