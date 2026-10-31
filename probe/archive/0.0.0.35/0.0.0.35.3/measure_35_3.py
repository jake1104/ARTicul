import wave
import hashlib
import numpy as np

SR = 22050


def load(path):
    raw = open(path, "rb").read()
    with wave.open(path, "rb") as w:
        n = w.getnframes()
        data = w.readframes(n)
    x = np.frombuffer(data, dtype=np.int16).astype(np.float64) / 32767.0
    return raw, n, x


def rms_db(v):
    return 20 * np.log10(max(float(np.sqrt((v * v).mean())), 1e-9))


def trough_max_db(x):
    w = SR // 100
    nw = len(x) // w
    nrms = np.sqrt((x[:nw * w].reshape(nw, w) ** 2).mean(axis=1))
    prev, end, worst = 10, nw - 15, 0.0
    for k in range(prev, end):
        ctx = float(nrms[k - prev:k].mean())
        if ctx <= 1e-9 or nrms[k] <= 1e-9:
            continue
        worst = min(worst, 20.0 * np.log10(float(nrms[k]) / ctx))
    return worst


def centroid_mag(x):
    m = len(x)
    win = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(m) / m)
    spec = np.abs(np.fft.rfft(x * win))
    freqs = np.fft.rfftfreq(m, 1.0 / SR)
    return float((freqs * spec).sum() / max(spec.sum(), 1e-12))


def estimate_f2(seg):
    mm = len(seg)
    ww = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(mm) / mm)
    best_f, best_p = 0.0, -1.0
    for b in range(int(np.ceil(700 * mm / SR)), int(1500 * mm / SR) + 1):
        if b > mm // 2:
            break
        ang = 2 * np.pi * b * np.arange(mm) / mm
        re = float((seg * ww * np.cos(ang)).sum())
        im = float((seg * ww * np.sin(ang)).sum())
        pp = re * re + im * im
        if pp > best_p:
            best_p, best_f = pp, b * SR / mm
    return best_f


print("=== Part A: new demos (report-only vs 34.3/33.2 baselines) ===")
for label, path in [("hello", "demo/hello.wav"),
                    ("annyeong", "demo/annyeonghaseyo.wav"),
                    ("yeobo", "demo/yeoboseyo.wav")]:
    raw, n, x = load(path)
    peak = float(np.max(np.abs(x)))
    grms = float(np.sqrt((x * x).mean()))
    h0, h1 = rms_db(x[:n // 2]), rms_db(x[n // 2:])
    n3 = n // 3
    t3 = float(np.sqrt((x[2 * n3:] ** 2).mean()))
    print("== %s: bytes=%d sha256=%s" % (label, len(raw), hashlib.sha256(raw).hexdigest()))
    print("   samples=%d (%.1fms) rms=%.4f (%.2fdBFS) peak=%.4f clamp>=0.985:%d" % (
        n, n / SR * 1000.0, grms, rms_db(x), peak, int((np.abs(x) >= 0.985).sum())))
    print("   halves %.2f/%.2f diff=%+.2f (|diff|<=5 -> %s; 2nd>-32 -> %s) centroid=%.1fHz trough=%.2fdB tail-third-rms=%.4f" % (
        h0, h1, h1 - h0, "PASS" if abs(h1 - h0) <= 5.0 else "FAIL",
        "PASS" if h1 > -32.0 else "FAIL", centroid_mag(x), trough_max_db(x), t3))

print("=== Part B: hello GOAT F2 (span per 33.2: o_start=1720+1389+1544-3*176) ===")
_, _, x = load("demo/hello.wav")
o_start = 1720 + 1389 + 1544 - 3 * 176
start = o_start + 176 + 110
span = x[start:]
nw, wlen = 6, len(span) // 6
f2s = [estimate_f2(span[k * wlen:(k + 1) * wlen]) for k in range(nw)]
print("hello F2 trajectory", [round(v, 1) for v in f2s])
print("hello F2 rise overall %.1f (gate >=100 -> %s; monotonic 50Hz tol -> %s)" % (
    f2s[-1] - f2s[0],
    "PASS" if f2s[-1] - f2s[0] >= 100.0 else "FAIL",
    "PASS" if all(f2s[k + 1] >= f2s[k] - 50.0 for k in range(nw - 1)) else "FAIL"))

print("=== Part C: lifelike spot-check on sustain_a.wav (rendered a:a:) ===")
_, n, xs = load("probe/0.0.0.35.3/sustain_a.wav")
print("sustain samples=%d" % n)
REG_A, REG_B = 441, 3087
F0 = 149.0
region = xs[REG_A:REG_B]
t0n = SR / F0
h, tbase = 60, 700
tmpl = region[tbase - 70:tbase - 70 + (2 * h + 21)].copy()
shifts = []
k = 0
while True:
    a = tbase + k * t0n
    ai = int(round(a))
    if ai < h or ai + h + 1 >= len(region):
        break
    seg = region[ai - h:ai + h + 1]
    cv = [float(seg @ tmpl[10 + s:10 + s + len(seg)]) for s in range(-10, 11)]
    bi = int(np.argmax(cv))
    if 0 < bi < len(cv) - 1:
        d = cv[bi - 1] - 2.0 * cv[bi] + cv[bi + 1]
        bg = 0.5 * (cv[bi - 1] - cv[bi + 1]) / d if abs(d) > 1e-12 else 0.0
    else:
        bg = 0.0
    shifts.append((bi - 10.0) + max(-1.0, min(1.0, bg)))
    k += 1
periods = np.array([t0n + shifts[i + 1] - shifts[i] for i in range(len(shifts) - 1)])
mean = periods.mean()
jit = float(np.abs(np.diff(periods)).mean() / mean)
print("jitter: n_periods=%d local_jitter=%.4f (band 0.005-0.010 -> %s)" % (
    len(periods), jit, "PASS" if 0.005 <= jit <= 0.010 else "FAIL"))


def autocorr_f0_tracked(seg, guess):
    v = seg - seg.mean()
    e0 = float(v @ v)
    if e0 <= 1e-12:
        return None
    if guess is None:
        lo, hi = round(SR / 250.0), round(SR / 70.0)
    else:
        c = SR / guess
        lo, hi = int(c / 1.12), int(c * 1.12)
    top = min(hi, len(v) - 1)
    if top <= lo:
        return None
    vals = np.array([float(v[:len(v) - lag] @ v[lag:]) / e0 for lag in range(lo, top + 1)])
    best = int(np.argmax(vals))
    if best == 0 or best + 1 >= len(vals):
        return None
    y0, y1, y2 = vals[best - 1], vals[best], vals[best + 1]
    denom = y0 - 2.0 * y1 + y2
    shift = 0.5 * (y0 - y2) / denom if abs(denom) > 1e-3 * abs(y1) else 0.0
    return SR / (lo + best + max(-1.0, min(1.0, shift)))


def k1_phase(frame, f0_guess):
    nn = 16384
    m = len(frame)
    win = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(m) / m)
    spec = np.fft.rfft(frame * win, n=nn)
    bin_w = SR / nn
    return float(np.angle(spec[min(int(round(f0_guess / bin_w)), nn // 2 - 1)]))


FRAME_LEN, FRAME_HOP = 441, 441
starts, s = [], 0
while s + FRAME_LEN <= len(region):
    starts.append(s)
    s += FRAME_HOP
f0s, phases, guess = [], [], None
for st in starts:
    f0 = autocorr_f0_tracked(region[st:st + FRAME_LEN], guess)
    if f0 is None:
        f0 = autocorr_f0_tracked(region[st:st + FRAME_LEN], None)
    guess = f0
    f0s.append(f0)
    phases.append(k1_phase(region[st:st + FRAME_LEN], f0))
resids = []
for j in range(1, len(phases)):
    fb = 0.5 * (f0s[j - 1] + f0s[j])
    pred = 2.0 * np.pi * fb * FRAME_HOP / SR
    v = phases[j] - phases[j - 1] - pred
    resids.append((v + np.pi) % (2 * np.pi) - np.pi)
rr = np.array(resids)
r = float(min(1.0, np.sqrt(((np.sin(rr)).mean()) ** 2 + ((np.cos(rr)).mean()) ** 2)))
cstd = float(np.sqrt(-2.0 * np.log(r))) if r > 1e-9 else float("inf")
print("k1: n_frames=%d circular_std=%.3f rad (>0.14 gate; >0.12 floor -> %s)" % (
    len(starts), cstd, "PASS" if cstd > 0.12 else "FAIL"))

WIN_LEN, WIN_HOP = 441, 100
wstarts, ws = [], REG_A
while ws + WIN_LEN <= REG_B:
    wstarts.append(ws)
    ws += WIN_HOP
wf0s, g = [], None
for st in wstarts:
    f0 = autocorr_f0_tracked(xs[st:st + WIN_LEN], g)
    if f0 is None:
        f0 = autocorr_f0_tracked(xs[st:st + WIN_LEN], None)
    g = f0
    wf0s.append(f0)
wf = np.array(wf0s)
ii = np.arange(len(wf))
cx, cy = ii.mean(), wf.mean()
sxx = ((ii - cx) ** 2).sum()
slope = ((ii - cx) * (wf - cy)).sum() / sxx if sxx > 1e-9 else 0.0
det = wf - slope * (ii - cx)
rel = float(det.std() / det.mean())
print("microtremor: n_win=%d detrended_rel_std=%.4f (>=0.004 -> %s)" % (
    len(wstarts), rel, "PASS" if rel >= 0.004 else "FAIL"))

print("=== Part D: spot table (six eval corpus items, report-only) ===")
for name in ["fixed_sentence", "demo_hello", "creak_probe", "gain_probe", "cluster_probe", "pause_probe"]:
    p = "probe/0.0.0.35.3/spot/%s.wav" % name
    raw, nn, xx = load(p)
    grms = float(np.sqrt((xx * xx).mean()))
    print("%-14s samples=%5d rms=%7.2fdBFS centroid=%8.1fHz sha=%s" % (
        name, nn, 20 * np.log10(max(grms, 1e-9)), centroid_mag(xx),
        hashlib.sha256(raw).hexdigest()[:16]))
_, _, xl = load("demo/hello.wav")
_, _, xsp = load("probe/0.0.0.35.3/spot/demo_hello.wav")
print("demo_hello spot-vs-live byte-identical:", bool((xl.shape == xsp.shape) and (xl == xsp).all()),
      "(expected False: spot uses old input hE loU, live uses h@ loU)")
