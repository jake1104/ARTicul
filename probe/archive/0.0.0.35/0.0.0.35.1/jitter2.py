import wave
import numpy as np

SR = 22050


def load(path):
    with wave.open(path, "rb") as w:
        n = w.getnframes()
        data = w.readframes(n)
    x = np.frombuffer(data, dtype=np.int16).astype(np.float64) / 32767.0
    return n, x


def brickwall(x, flo=100.0, fhi=200.0):
    X = np.fft.rfft(x)
    fr = np.fft.rfftfreq(len(x), 1.0 / SR)
    mask = (fr >= flo) & (fr <= fhi)
    Y = np.zeros_like(X)
    Y[mask] = X[mask]
    return np.fft.irfft(Y, n=len(x))


def rising_crossings(y):
    tc = []
    for i in range(len(y) - 1):
        if y[i] <= 0 < y[i + 1]:
            f = -y[i] / (y[i + 1] - y[i] + 1e-18)
            tc.append(i + f)
    return np.array(tc)


def local_jitter(tc):
    T = np.diff(tc)
    T = T[np.isfinite(T)]
    return 100.0 * float(np.mean(np.abs(np.diff(T)))) / float(T.mean()), len(T)


def hilbert_env(x):
    X = np.fft.rfft(x)
    H = np.zeros_like(X)
    H[0] = 1.0
    H[1:] = 2.0
    return np.abs(np.fft.irfft(X * H, n=len(x)))


nn, v = load("probe/0.0.0.35.1/solo_a_nospace.wav")
seg = v[441:3087]
print("engine seg1: n=%d" % len(seg))

for tag, sig in [("engine", seg)]:
    y = brickwall(sig)
    tc = rising_crossings(y)
    j, m = local_jitter(tc)
    env = hilbert_env(sig)
    ci = np.clip((tc[1:] + tc[:-1]) / 2, 0, len(sig) - 1).astype(int)
    a = env[ci]
    sh = 100.0 * float(np.mean(np.abs(np.diff(a)))) / float(a.mean())
    print("%s: crossings=%d jitter-local=%.4f%% shimmer-env=%.4f%%" % (tag, m, j, sh))

rng = np.random.default_rng(0)
N = len(seg)
t = np.arange(N) / SR
F0 = 149.0
# control 1: pure tone (method floor)
c1 = np.sin(2 * np.pi * F0 * t)
# control 2: natural-level perturbations (0.7pct iid jitter + 3.5Hz 0.8pct tremor + 3pct shimmer)
per = int(round(SR / F0))
ph = np.zeros(N)
f_inst = F0 * (1 + 0.008 * np.sin(2 * np.pi * 3.5 * t) + 0.007 * rng.standard_normal(N) / 3.0 * 3.0)
f_inst = F0 * (1 + 0.008 * np.sin(2 * np.pi * 3.5 * t)) 
j = 0.007 * rng.standard_normal(N)
ph[1:] = np.cumsum(2 * np.pi * (F0 * (1 + 0.008 * np.sin(2 * np.pi * 3.5 * t[1:])) / SR + j[1:] / per))
amp = 1 + 0.03 * rng.standard_normal(N)
c2 = np.sin(ph) * amp
for tag, sig in [("pure-tone", c1), ("natural-level", c2)]:
    y = brickwall(sig)
    tc = rising_crossings(y)
    j, m = local_jitter(tc)
    env = hilbert_env(sig)
    ci = np.clip((tc[1:] + tc[:-1]) / 2, 0, len(sig) - 1).astype(int)
    a = env[ci]
    sh = 100.0 * float(np.mean(np.abs(np.diff(a)))) / float(a.mean())
    print("%s: crossings=%d jitter-local=%.4f%% shimmer-env=%.4f%%" % (tag, m, j, sh))
