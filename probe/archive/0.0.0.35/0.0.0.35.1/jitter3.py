import wave
import numpy as np

LOGPATH = "logs/0.0.0.35.1/probe.log"
_log = []


def emit(s):
    print(s, flush=True)
    _log.append(s)

SR = 22050


def load(path):
    with wave.open(path, "rb") as w:
        n = w.getnframes()
        data = w.readframes(n)
    x = np.frombuffer(data, dtype=np.int16).astype(np.float64) / 32767.0
    return n, x


def lowpass(x, fc=400.0):
    a = float(np.exp(-2 * np.pi * fc / SR))
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    z = np.empty_like(x)
    acc = 0.0
    for i in range(len(x) - 1, -1, -1):
        acc = (1 - a) * y[i] + a * acc
        z[i] = acc
    return z


def rising_crossings(y):
    tc = []
    for i in range(len(y) - 1):
        if y[i] <= 0 < y[i + 1]:
            f = -y[i] / (y[i + 1] - y[i] + 1e-18)
            tc.append(i + f)
    return np.array(tc)


def local_jitter(tc):
    T = np.diff(tc)
    return 100.0 * float(np.mean(np.abs(np.diff(T)))) / float(T.mean()), len(T)


# 1) exact construction jitter: replicate source.rs phase accumulation (lcg11, seed 0x12345678)
rng_state = 0x12345678


def lcg11():
    global rng_state
    rng_state = (rng_state * 1664525 + 1013904223) & 0xFFFFFFFF
    return ((rng_state >> 8) & 0xFFFFFF) / 16777216.0 * 2.0 - 1.0


for F0 in (120.0, 149.0):
    rng_state = 0x12345678
    phase = 0.0
    prev = 0.0
    marks = []
    for i in range(22050):
        jit = 1.0 + 0.008 * lcg11()
        phase += F0 * jit / SR
        cyc = phase % 1.0
        if cyc < prev:
            frac = (1.0 - prev) / ((cyc + 1.0 - prev) + 1e-18)
            marks.append(i - 1 + frac)
        prev = cyc
    marks = np.array(marks, dtype=np.float64)
    j, m = local_jitter(marks)
    T = np.diff(marks)
    T = T - T.mean()
    lag1 = float((T[:-1] * T[1:]).sum() / (T * T).sum())
    emit("construction jitter F0=%.0f: local=%.4f%% lag1=%+.4f (n=%d)" % (F0, j, lag1, m))

# 2) waveform zero-crossing jitter on lowpassed engine output (glide detrended)
_, v = load("probe/0.0.0.35.1/solo_a_nospace.wav")
seg = v[441:3087]
lp = lowpass(seg) - np.mean(lowpass(seg))
tc = rising_crossings(lp)
T = np.diff(tc)
j, m = local_jitter(tc)
emit("engine waveform zc: crossings=%d jitter-local=%.4f%% (harmonic-interference artifact, see text)" % (m, j))
ii = np.arange(len(T))
A = np.vstack([ii, np.ones_like(ii)]).T
coef, _, _, _ = np.linalg.lstsq(A, T, rcond=None)
r = T - (coef[0] * ii + coef[1])
jd = 100.0 * float(np.mean(np.abs(np.diff(r)))) / float(T.mean())
emit("engine waveform zc detrended: jitter-local=%.4f%% slope=%.5f samp/period" % (jd, coef[0]))
with open(LOGPATH, "a") as fh:
    fh.write("--- jitter3.py (exact-construction jitter + zc cross-check) ---\n")
    fh.write("\n".join(_log) + "\n")
