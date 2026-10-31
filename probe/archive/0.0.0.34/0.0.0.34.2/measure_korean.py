import wave
import hashlib
import numpy as np

SR = 22050
M64 = (1 << 64) - 1
SALT = 0x9E3779B97F4A7C15

V1 = {"a": (690.0, 1165.0), "V": (585.0, 1085.0), "e": (479.0, 1919.0), "o": (441.0, 740.0)}
F1BAND = {
    "a": (656.0, 725.0),
    "V": (538.0, 632.0),
    "e": (359.0, 599.0),
    "o": (397.0, 485.0),
}
VOWELS = {
    "annyeong": [
        ("a", (1216.0, 1398.0), 1307.0),
        ("V", (998.0, 1172.0), 1085.0),
        ("a", (1348.0, 1551.0), 1449.5),
        ("e", (1823.0, 2015.0), 1919.0),
        ("o", (703.0, 777.0), 740.0),
    ],
    "yeobo": [
        ("V", (985.0, 1134.0), 1059.5),
        ("o", (1229.0, 1415.0), 1322.0),
        ("e", (1823.0, 2015.0), 1919.0),
        ("o", (703.0, 777.0), 740.0),
    ],
}


def splitmix64(x):
    x = (x + 0x9E3779B97F4A7C15) & M64
    z = x
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M64
    return z ^ (z >> 31)


def variance(i):
    return 1.0 + 0.12 * (splitmix64(i ^ SALT) / float(1 << 64) - 0.5)


UNITS = {
    "annyeong": [
        ("a", 180.0, True), ("n", 90.0, False), ("n", 90.0, False), ("j", 90.0, False),
        ("V", 155.0, True), ("N", 90.0, False), ("h\\", 110.0, False), ("a", 180.0, True),
        ("s", 130.0, False), ("e", 160.0, True), ("j", 90.0, False), ("o", 160.0, True),
    ],
    "yeobo": [
        ("j", 90.0, False), ("V", 155.0, True), ("b", 90.0, False), ("o", 160.0, True),
        ("s", 130.0, False), ("e", 160.0, True), ("j", 90.0, False), ("o", 160.0, True),
    ],
}

WORD_SYL = {"annyeong": [1, 1, 3], "yeobo": [4]}


def units_for_word(units, word_syl, wi):
    off = sum(nunits_for_word(units, word_syl, w) for w in range(wi))
    n = nunits_for_word(units, word_syl, wi)
    return units[off:off + n]


def nunits_for_word(units, word_syl, wi):
    return WORD_NUNITS[(tuple(word_syl), wi)]


WORD_NUNITS = {((1, 1, 3), 0): 2, ((1, 1, 3), 1): 4, ((1, 1, 3), 2): 6, ((4,), 0): 8}


def plan_durations(label):
    units = UNITS[label]
    word_syl = WORD_SYL[label]
    durs = []
    fi = 0
    for wi, nsyl in enumerate(word_syl):
        chunk = units_for_word(units, word_syl, wi)
        last_v = max(i for i, (_, _, v) in enumerate(chunk) if v)
        for k, (sym, base, isv) in enumerate(chunk):
            ctx = 1.0
            if isv or sym in ("n", "N", "j"):
                nxt = chunk[k + 1][0] if k + 1 < len(chunk) else None
                if nxt is None and wi + 1 < len(word_syl):
                    nxt = units_for_word(units, word_syl, wi + 1)[0][0]
                if nxt in ("s", "k", "t", "p", "h"):
                    ctx = 0.78
            poly = 1.0 if nsyl <= 1 else (0.9 if nsyl == 2 else 0.8)
            cluster = 0.8 if (not isv and fi > 0 and not units[fi - 1][2]) else 1.0
            initial = 1.1 if (k == 0 and not isv) else 1.0
            final = 1.6 if (wi == len(word_syl) - 1 and k >= last_v) else 1.0
            capped = max(ctx, 0.5)
            floor = 40.0 if isv else (50.0 if sym in ("s", "h\\") else 30.0)
            ms = round(max(base * capped * poly * cluster * final * initial * variance(fi), floor))
            durs.append(ms)
            fi += 1
    return durs


def unit_bounds(durs):
    short = int(0.008 * SR)
    bounds = [0]
    acc = 0
    for i, ms in enumerate(durs):
        n = max(1, int(round(ms / 1000.0 * SR)))
        if i > 0:
            acc -= min(short, acc)
        acc += n
        bounds.append(acc)
    return bounds


def load(path):
    raw = open(path, "rb").read()
    with wave.open(path, "rb") as w:
        n = w.getnframes()
        data = w.readframes(n)
    x = np.frombuffer(data, dtype=np.int16).astype(np.float64) / 32767.0
    return raw, n, x


def rms_db(v):
    return 20 * np.log10(max(float(np.sqrt((v * v).mean())), 1e-9))


def centroid(x):
    m = len(x)
    win = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(m) / m)
    spec = np.abs(np.fft.rfft(x * win))
    freqs = np.fft.rfftfreq(m, 1.0 / SR)
    return float((freqs * spec).sum() / max(spec.sum(), 1e-12))


def trough(x):
    w = SR // 100
    nw = len(x) // w
    nrms = np.sqrt((x[:nw * w].reshape(nw, w) ** 2).mean(axis=1))
    worst = 0.0
    for k in range(10, nw - 15):
        ctx = float(nrms[k - 10:k].mean())
        if ctx <= 1e-9 or nrms[k] <= 1e-9:
            continue
        worst = min(worst, 20.0 * np.log10(float(nrms[k]) / ctx))
    return worst


def smooth(power, width=12):
    return np.convolve(power, np.ones(2 * width + 1) / (2 * width + 1), mode="same")


def formant_peaks(seg, flo, fhi):
    m = len(seg)
    n = 1
    while n < m:
        n *= 2
    n = max(64, min(n, 8192))
    win = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(m) / m)
    buf = np.zeros(n)
    buf[:m] = seg * win
    spec = np.abs(np.fft.rfft(buf)) ** 2 / n
    freqs = np.fft.rfftfreq(n, 1.0 / SR)
    sm = smooth(spec)
    ref = np.median(spec[(freqs >= 300.0) & (freqs <= 3000.0)])
    lo = int(np.floor(flo / SR * n)) + 1
    hi = int(np.ceil(fhi / SR * n)) - 1
    lo = max(lo, 3)
    hi = min(hi, len(spec) - 3)
    best = None
    for k in range(lo + 2, hi - 1):
        if sm[k] > sm[k - 1] and sm[k] > sm[k - 2] and sm[k] >= sm[k + 1] and sm[k] >= sm[k + 2] and sm[k] > 2.0 * ref:
            if best is None or sm[k] > sm[best]:
                best = k
    if best is not None:
        return float(freqs[best]), True
    arg = lo + int(np.argmax(sm[lo:hi + 1]))
    return float(freqs[arg]), False


def autocorr_f0(seg):
    x = seg - seg.mean()
    e0 = float((x * x).sum())
    if e0 <= 1e-12:
        return float("nan")
    lo, hi = int(round(SR / 250.0)), int(round(SR / 70.0))
    best_lag, best_v = 0, -1.0
    for lag in range(lo, min(hi, len(x) - 1) + 1):
        v = float((x[:len(x) - lag] * x[lag:]).sum()) / e0
        if v > best_v:
            best_v, best_lag = v, lag
    return SR / best_lag if best_lag else float("nan")


for label, path, text in [
    ("annyeong", "probe/0.0.0.34.2/annyeonghaseyo-korean.wav", None),
    ("yeobo", "probe/0.0.0.34.2/yeoboseyo-korean.wav", None),
]:
    raw, n, x = load(path)
    peak = float(np.max(np.abs(x)))
    grms = float(np.sqrt((x * x).mean()))
    h0, h1 = rms_db(x[:n // 2]), rms_db(x[n // 2:])
    print("== %s: bytes=%d sha256=%s" % (label, len(raw), hashlib.sha256(raw).hexdigest()))
    print("   samples=%d (%.1fms) rms=%.4f (%.2fdBFS) peak=%.4f clamp>=0.985: %d" % (
        n, n / SR * 1000.0, grms, rms_db(x), peak, int((np.abs(x) >= 0.985).sum())))
    print("   halves %.2f/%.2fdBFS diff=%+.2f centroid=%.1fHz trough=%.2fdB" % (h0, h1, h1 - h0, centroid(x), trough(x)))
    durs = plan_durations(label)
    bounds = unit_bounds(durs)
    print("   planned_bounds_total=%d render_len=%d drift=%d" % (bounds[-1], n, bounds[-1] - n))
    vi = 0
    for i, (sym, base, isv) in enumerate(UNITS[label]):
        if not isv:
            continue
        vsym, (f2lo, f2hi), pred2 = VOWELS[label][vi]
        assert vsym == sym, (vsym, sym)
        a, b = bounds[i], bounds[i + 1]
        seg = x[a + (b - a) // 4:a + 3 * (b - a) // 4]
        f1lo, f1hi = F1BAND[sym]
        f1, q1 = formant_peaks(seg, f1lo, f1hi)
        f2, q2 = formant_peaks(seg, f2lo, f2hi)
        c = (a + b) // 2
        f0 = autocorr_f0(x[c - 330:c + 330])
        nf1, nf2 = V1[sym]
        d1 = (f1 - nf1) / nf1 * 100.0
        d2 = (f2 - nf2) / nf2 * 100.0
        dp = (f2 - pred2) / pred2 * 100.0
        print("   vowel%d %s: F1=%.0f%s (norm %.0f, %+.1f%%) F2=%.0f%s (norm %.0f, %+.1f%%; pred %.0f, %+.1f%%) f0=%.1fHz (%+.2fst)" % (
            vi, sym, f1, "" if q1 else "*", nf1, d1, f2, "" if q2 else "*", nf2, d2, pred2, dp,
            f0, 12 * np.log2(f0 / 120.0)))
        vi += 1
