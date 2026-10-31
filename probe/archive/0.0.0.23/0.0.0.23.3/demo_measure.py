import wave
import hashlib
import numpy as np

SR = 22050
DEMOS = [
    ("hello", "demo/hello.wav"),
    ("annyeong", "demo/annyeonghaseyo.wav"),
    ("yeobo", "demo/yeoboseyo.wav"),
]


def load(path):
    raw = open(path, "rb").read()
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        nch = w.getnchannels()
        n = w.getnframes()
        data = w.readframes(n)
    x = np.frombuffer(data, dtype=np.int16).astype(np.float64) / 32767.0
    return raw, sr, nch, n, x


def rms_db(v):
    return 20 * np.log10(max(float(np.sqrt((v * v).mean())), 1e-9))


def trough_max_db(x):
    w = SR // 100
    nw = len(x) // w
    nrms = np.sqrt((x[:nw * w].reshape(nw, w) ** 2).mean(axis=1))
    prev = 10
    end = nw - 15
    worst = 0.0
    for k in range(prev, end):
        ctx = float(nrms[k - prev:k].mean())
        if ctx <= 1e-9 or nrms[k] <= 1e-9:
            continue
        d = 20.0 * np.log10(float(nrms[k]) / ctx)
        worst = min(worst, d)
    return worst


def centroid_mag(x, sr):
    m = len(x)
    win = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(m) / m)
    spec = np.abs(np.fft.rfft(x * win))
    freqs = np.fft.rfftfreq(m, 1.0 / sr)
    return float((freqs * spec).sum() / max(spec.sum(), 1e-12))


def band_split(x):
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    freqs = np.fft.rfftfreq(len(x), 1.0 / SR)
    tot = float(spec.sum())
    lo = float(spec[freqs < 300.0].sum()) / tot
    mid = float(spec[(freqs >= 300.0) & (freqs < 3400.0)].sum()) / tot
    hi = float(spec[freqs >= 4000.0].sum()) / tot
    return lo, mid, hi


def estimate_f2(seg, sr):
    mm = len(seg)
    ww = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(mm) / mm)
    best_f, best_p = 0.0, -1.0
    for b in range(int(np.ceil(700 * mm / sr)), int(1500 * mm / sr) + 1):
        if b > mm // 2:
            break
        ang = 2 * np.pi * b * np.arange(mm) / mm
        re = float((seg * ww * np.cos(ang)).sum())
        im = float((seg * ww * np.sin(ang)).sum())
        pp = re * re + im * im
        if pp > best_p:
            best_p, best_f = pp, b * sr / mm
    return best_f


for label, path in DEMOS:
    raw, sr, nch, n, x = load(path)
    peak = float(np.max(np.abs(x)))
    grms = float(np.sqrt((x * x).mean()))
    h0, h1 = rms_db(x[:n // 2]), rms_db(x[n // 2:])
    lo, mid, hi = band_split(x)
    n3 = n // 3
    thirds = [rms_db(x[0:n3]), rms_db(x[n3:2 * n3]), rms_db(x[2 * n3:])]
    print("== %s (%s): bytes=%d sha256=%s" % (label, path, len(raw), hashlib.sha256(raw).hexdigest()))
    print("   samples=%d sr=%d ch=%d dur=%.1fms" % (n, sr, nch, n / sr * 1000.0))
    print("   global rms=%.4f (%.2fdBFS) peak=%.4f gate: rms>=0.10 peak<=0.99 -> %s"
          % (grms, rms_db(x), peak, "PASS" if grms >= 0.10 and peak <= 0.99 else "FAIL"))
    print("   halves rms1=%.2fdBFS rms2=%.2fdBFS diff=%+.2fdB (|diff|<=5.0 -> %s; floor2>-32 -> %s)"
          % (h0, h1, h1 - h0, "PASS" if abs(h1 - h0) <= 5.0 else "FAIL",
             "PASS" if h1 > -32.0 else "FAIL"))
    print("   centroid=%.1fHz" % centroid_mag(x, sr))
    print("   trough max depth=%.2fdB (gate >=-12 -> %s)"
          % (trough_max_db(x), "PASS" if trough_max_db(x) >= -12.0 else "FAIL"))
    print("   thirds rms=%.2f/%.2f/%.2fdBFS" % tuple(thirds))
    print("   band energy: 0-300Hz=%.3f 300-3400Hz=%.3f 4k+Hz=%.3f" % (lo, mid, hi))

# hello F2 rise (same recipe as demo_measure 0.0.0.20.3)
_, _, _, _, x = load("demo/hello.wav")
o_start = 1720 + 1962 + 1544 - 3 * 176
start = o_start + 176 + 110
span = x[start:]
nw = 6
wlen = len(span) // nw
f2s = [estimate_f2(span[k * wlen:(k + 1) * wlen], SR) for k in range(nw)]
print("hello F2 trajectory", [round(v, 1) for v in f2s])
print("hello F2 rise overall %.1f (gate >=100 -> %s; monotonic 50Hz tol -> %s)"
      % (f2s[-1] - f2s[0],
         "PASS" if f2s[-1] - f2s[0] >= 100.0 else "FAIL",
         "PASS" if all(f2s[k + 1] >= f2s[k] - 50.0 for k in range(nw - 1)) else "FAIL"))
