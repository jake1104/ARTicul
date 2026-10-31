import wave
import hashlib
import numpy as np

P = "demo/hello.wav"
SR = 22050
raw = open(P, "rb").read()
print("bytes", len(raw), "sha256", hashlib.sha256(raw).hexdigest())

with wave.open(P, "rb") as w:
    sr = w.getframerate()
    nch = w.getnchannels()
    nframes = w.getnframes()
    data = w.readframes(nframes)
x = np.frombuffer(data, dtype=np.int16).astype(np.float64) / 32767.0
print("samples", len(x), "sr", sr, "ch", nch)


def rms_db(v):
    return 20 * np.log10(max(np.sqrt(float((v * v).mean())), 1e-9))


def peak_db(v):
    return 20 * np.log10(max(float(np.max(np.abs(v))), 1e-9))


n = len(x)
h0, h1 = rms_db(x[: n // 2]), rms_db(x[n // 2 :])
print("halves rms1=%.1f rms2=%.1f diff=%+.2fdB" % (h0, h1, h1 - h0))

h_win = x[200:1344]
o_win = x[5600:7000]
print("peak whole=%.2fdBFS h-interior[200:1344]=%.2fdBFS o-interior[5600:7000]=%.2fdBFS"
      % (peak_db(x), peak_db(h_win), peak_db(o_win)))
print("rms h-interior=%.2fdBFS o-interior=%.2fdBFS"
      % (rms_db(h_win), rms_db(o_win)))

m = len(x)
w = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(m) / m)
spec = np.abs(np.fft.rfft(x * w))
freqs = np.fft.rfftfreq(m, 1.0 / sr)
cent = float((freqs * spec).sum() / max(spec.sum(), 1e-12))
pspec = spec ** 2
pcent = float((freqs * pspec).sum() / max(pspec.sum(), 1e-12))
print("centroid magnitude-weighted %.1fHz power-weighted %.1fHz" % (cent, pcent))

o_start = 1720 + 1962 + 1544 - 3 * 176
start = o_start + 176 + 110
span = x[start:]
nw = 6
wlen = len(span) // nw
f2s = []
for k in range(nw):
    s = span[k * wlen:(k + 1) * wlen]
    mm = len(s)
    ww = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(mm) / mm)
    best_f, best_p = 0.0, -1.0
    for b in range(int(np.ceil(700 * mm / sr)), int(1500 * mm / sr) + 1):
        if b > mm // 2:
            break
        ang = 2 * np.pi * b * np.arange(mm) / mm
        re = float((s * ww * np.cos(ang)).sum())
        im = float((s * ww * np.sin(ang)).sum())
        pp = re * re + im * im
        if pp > best_p:
            best_p, best_f = pp, b * sr / mm
    f2s.append(best_f)
print("F2 trajectory", [round(v, 1) for v in f2s])
print("F2 rise overall %.1f" % (f2s[-1] - f2s[0],))
steps = [f2s[k + 1] - f2s[k] for k in range(nw - 1)]
print("F2 largest step down %.1f (tolerance 50Hz)" % min(min(steps), 0.0))


def ac_peak(seg, fmin=60, fmax=300):
    v = seg - seg.mean()
    e0 = float(v @ v)
    lo = max(1, sr // fmax)
    hi = min(len(v) - 1, sr // fmin)
    return max(float(v[: len(v) - lag] @ v[lag:]) / e0 for lag in range(lo, hi + 1))


tail = x[len(x) - int(0.080 * sr):]
print("final-80ms autocorr peak %.4f" % ac_peak(tail))

N_FFT = 8192


def notch_depth(seg):
    W = np.hanning(len(seg))
    S = np.abs(np.fft.rfft(seg * W, n=N_FFT)) ** 2
    freqs = np.fft.rfftfreq(N_FFT, 1.0 / SR)

    def med(lo, hi):
        m = (freqs >= lo) & (freqs < hi)
        return float(10.0 * np.log10(np.median(S[m])))

    edge = med(2000.0, 2300.0)
    core = med(2470.0, 2530.0)
    return edge, core, edge - core


for label, t0, t1 in [("pinned-170-210ms", 0.170, 0.210), ("wide-182-222ms", 0.182, 0.222)]:
    seg = x[int(t0 * SR):int(t1 * SR)]
    edge, core, depth = notch_depth(seg)
    print("l-notch %s N=%d edge=%.2fdB core=%.2fdB depth=%.2fdB"
          % (label, len(seg), edge, core, depth))
