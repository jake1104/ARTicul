import subprocess
import sys
import os
import wave
import hashlib
import numpy as np

SR = 22050
PROBE = "probe/0.0.0.35.1"
LOGDIR = "logs/0.0.0.35.1"
EXE = "target/release/articul.exe"

JOBS = [
    (['h@ "loU', "config/default-voice.toml", PROBE + "/fresh_hello.wav"], "hello"),
    (["%an njVN h\\asejo", "config/korean-voice.toml", PROBE + "/fresh_annyeong.wav"], "annyeong"),
    (["%jVbosejo", "config/korean-voice.toml", PROBE + "/fresh_yeobo.wav"], "yeobo"),
    (['"a:', "config/default-voice.toml", PROBE + "/solo_a_stressed.wav"], "stressed-a"),
    (["a:a:", "config/default-voice.toml", PROBE + "/solo_a_nospace.wav"], "nospace-aa"),
]


def load(path):
    raw = open(path, "rb").read()
    with wave.open(path, "rb") as w:
        n = w.getnframes()
        data = w.readframes(n)
    x = np.frombuffer(data, dtype=np.int16).astype(np.float64) / 32767.0
    return raw, n, x


def autocorr_f0_peak(seg, fmin=60.0, fmax=300.0):
    x = seg - seg.mean()
    e0 = float((x * x).sum())
    if e0 <= 1e-12:
        return float("nan"), 0.0
    lo = int(round(SR / fmax))
    hi = int(round(SR / fmin))
    best_lag, best_v = 0, -1.0
    for lag in range(lo, min(hi, len(x) - 1) + 1):
        v = float((x[:len(x) - lag] * x[lag:]).sum()) / e0
        if v > best_v:
            best_v, best_lag = v, lag
    if best_lag == 0:
        return float("nan"), 0.0
    return SR / best_lag, best_v


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


def peak_indices(x, min_dist):
    idx = []
    last = -min_dist - 1
    for i in range(1, len(x) - 1):
        if x[i] >= x[i - 1] and x[i] > x[i + 1] and i - last >= min_dist:
            idx.append(i)
            last = i
    return np.array(idx, dtype=np.int64)


def lag1(x):
    x = np.asarray(x, dtype=np.float64)
    x = x - x.mean()
    d = float((x * x).sum())
    if d <= 1e-18 or len(x) < 4:
        return float("nan")
    return float((x[:-1] * x[1:]).sum() / d)


def period_analysis(x, f0guess, label, p):
    P = SR / f0guess
    lp = lowpass(x)
    pk = peak_indices(lp, int(0.8 * P))
    periods = np.diff(pk).astype(np.float64)
    periods = periods[(periods > 0.6 * P) & (periods < 1.6 * P)]
    pj = 100.0 * float(np.mean(np.abs(np.diff(periods)))) / float(periods.mean())
    p("%s: f0guess=%.1fHz periods=%d mean=%.2fsamples jitter-local=%.4f%%" % (
        label, f0guess, len(periods), float(periods.mean()), pj))
    amps = np.array([float(np.max(np.abs(x[i:int(i + P)]))) for i in pk[:-1]
                     if i + int(P) <= len(x)])
    amps = amps[amps > 1e-6]
    sh = 100.0 * float(np.mean(np.abs(np.diff(amps)))) / float(amps.mean())
    sh_db = float(np.mean(np.abs(20.0 * np.log10(amps[1:] / amps[:-1]))))
    p("%s: shimmer-local=%.4f%% = %.4fdB (n=%d)" % (label, sh, sh_db, len(amps)))
    p("%s: lag1(periods)=%.4f lag1(amps)=%.4f" % (label, lag1(periods), lag1(amps)))
    return pj, sh, sh_db, len(periods)


def main():
    lines = []
    p = lambda s="": (lines.append(s), print(s, flush=True))
    p("0.0.0.35.1 machineness probe session")
    p("render jobs (exact argv via subprocess, no shell quoting):")
    for (text, voice, out), label in JOBS:
        r = subprocess.run([EXE, "synthesize", "--text", text, "--voice", voice, "--out", out],
                           capture_output=True, text=True)
        p("  %s: rc=%d %s %s" % (label, r.returncode, r.stdout.strip(), r.stderr.strip()))
        if r.returncode != 0:
            raise SystemExit(1)
    p("")
    p("byte-identity vs shipped demos:")
    for fresh, ship in [(PROBE + "/fresh_hello.wav", "demo/hello.wav"),
                        (PROBE + "/fresh_annyeong.wav", "demo/annyeonghaseyo.wav"),
                        (PROBE + "/fresh_yeobo.wav", "demo/yeoboseyo.wav")]:
        a = open(fresh, "rb").read()
        b = open(ship, "rb").read()
        p("  %s vs %s: %d vs %d bytes, identical=%s sha256=%.16s" % (
            fresh, ship, len(a), len(b), a == b, hashlib.sha256(a).hexdigest()))
    p("")

    # ---- sustained vowel: FIRST segment interiors (non-final: no creak) ----
    _, nd, vd = load(PROBE + "/solo_a_double.wav")
    p("solo double (spaced): %d samples (%.1f ms)" % (nd, nd / SR * 1000.0))
    _, nn2, vn = load(PROBE + "/solo_a_nospace.wav")
    p("solo nospace a:a:: %d samples (%.1f ms)" % (nn2, nn2 / SR * 1000.0))
    winD, hopD = int(0.020 * SR), int(0.020 * SR)
    for tag, xx in (("spaced", vd), ("nospace", vn)):
        p("  [%s] 20ms frames (tms rms f0 peak):" % tag)
        for s in range(0, len(xx) - winD, hopD):
            seg = xx[s:s + winD]
            rms = float(np.sqrt((seg * seg).mean()))
            f, pkv = autocorr_f0_peak(seg)
            p("    t=%6.1fms rms=%.4f f0=%7.2f peak=%.3f" % (s / SR * 1000.0, rms, f, pkv))
    # clean interior: nospace seg1 [441, 3087] (20-140ms: F0 flat, no boundary, no creak)
    steady = vn[441:3087]
    fguess, pv = autocorr_f0_peak(steady)
    p("nospace seg1 interior [441,3087): F0 guess=%.2fHz (peak=%.3f)" % (fguess, pv))

    # (a)(b) period-synchronous jitter + shimmer (lowpass-prefiltered peak picking)
    pj, sh, sh_db, nper = period_analysis(steady, fguess, "(a)(b) seg1", p)

    # (c) harmonic phase coherence: residual phase after linear prediction
    fwin, fhop = int(0.050 * SR), int(0.005 * SR)
    starts = list(range(0, len(steady) - fwin, fhop))
    resid = {k: [] for k in range(1, 9)}
    for s0, s1 in zip(starts[:-1], starts[1:]):
        for s in (s0, s1):
            pass
        f, _ = autocorr_f0_peak(steady[s0:s0 + fwin])
        if not np.isfinite(f):
            continue
        for s in (s0, s1):
            pass
        m = 8192
        w = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(fwin) / fwin)
        spec = np.fft.rfft(steady[s0:s0 + fwin] * w, n=m)
        ph = np.angle(spec)
        fr = np.fft.rfftfreq(m, 1.0 / SR)
        for k in range(1, 9):
            b = int(np.argmin(np.abs(fr - k * f)))
            resid[k].append(ph[b])
    circ = []
    for k in range(1, 9):
        a = np.array(resid[k])
        if len(a) < 4:
            continue
        f, _ = autocorr_f0_peak(steady[len(steady) // 2 - fwin // 2:len(steady) // 2 + fwin // 2])
        pred = 2 * np.pi * k * f * fhop / SR
        d = (np.diff(a) - pred + np.pi) % (2 * np.pi) - np.pi
        r = float(np.abs(np.exp(1j * d).mean()))
        std = float(np.sqrt(-2 * np.log(max(r, 1e-12))))
        circ.append(std)
    p("(c) harmonic phase residual circular-std per harmonic (rad): %s" % (
        ", ".join("k%d=%.3f" % (k + 1, v) for k, v in enumerate(circ))))
    p("(c) mean phase residual std (k=1..%d) = %.4f rad" % (len(circ), float(np.mean(circ))))

    # inter-period waveform correlation (peaks on lowpassed waveform)
    lp = lowpass(steady)
    P1 = SR / fguess
    pkc = peak_indices(lp, int(0.8 * P1))
    segs = []
    for i in pkc:
        a0, b0 = int(i - P1), int(i + P1)
        if a0 < 0 or b0 > len(steady):
            continue
        s = steady[a0:b0]
        g = np.linspace(0, 1, 200)
        xs = np.linspace(0, 1, len(s))
        segs.append(np.interp(g, xs, s))
    segs = np.array(segs)
    cors = []
    for i in range(min(len(segs) - 1, 40)):
        a, b = segs[i] - segs[i].mean(), segs[i + 1] - segs[i + 1].mean()
        d = float(np.sqrt((a * a).sum() * (b * b).sum()))
        if d > 1e-12:
            cors.append(float((a * b).sum() / d))
    p("(c) inter-period waveform correlation: mean=%.6f min=%.6f (n=%d pairs)" % (
        float(np.mean(cors)), float(np.min(cors)), len(cors)))

    # (d) within-segment formant drift on the single-segment vowel
    dwin = int(0.030 * SR)
    f1s, f2s, c1s, c2s = [], [], [], []
    for s in range(0, len(steady) - dwin, dwin):
        seg = steady[s:s + dwin]
        m = 4096
        w = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(dwin) / dwin)
        pw = np.abs(np.fft.rfft(seg * w, n=m)) ** 2
        fr = np.fft.rfftfreq(m, 1.0 / SR)
        for flo, fhi, store in ((300.0, 1000.0, f1s), (800.0, 2600.0, f2s)):
            lo = int(np.searchsorted(fr, flo))
            hi = int(np.searchsorted(fr, fhi))
            k = lo + int(np.argmax(pw[lo:hi]))
            if 0 < k < len(pw) - 1 and pw[k] > 0:
                d = 0.5 * (pw[k - 1] - pw[k + 1]) / (pw[k - 1] - 2 * pw[k] + pw[k + 1] + 1e-18)
                d = float(np.clip(d, -0.5, 0.5))
                store.append(float(fr[k] + d * (fr[1] - fr[0])))
            else:
                store.append(float(fr[k]))
        b1 = (fr >= 300.0) & (fr <= 1000.0)
        b2 = (fr >= 1000.0) & (fr <= 2600.0)
        c1s.append(float((fr[b1] * pw[b1]).sum() / max(pw[b1].sum(), 1e-18)))
        c2s.append(float((fr[b2] * pw[b2]).sum() / max(pw[b2].sum(), 1e-18)))
    p("(d) single-segment steady vowel, %d frames x 30ms:" % len(f1s))
    p("    F1 peak-pick: mean=%.1fHz range=%.1fHz std=%.2fHz" % (
        float(np.mean(f1s)), float(np.max(f1s) - np.min(f1s)), float(np.std(f1s))))
    p("    F2 peak-pick: mean=%.1fHz range=%.1fHz std=%.2fHz" % (
        float(np.mean(f2s)), float(np.max(f2s) - np.min(f2s)), float(np.std(f2s))))
    p("    F1-band centroid: mean=%.1fHz range=%.1fHz std=%.2fHz" % (
        float(np.mean(c1s)), float(np.max(c1s) - np.min(c1s)), float(np.std(c1s))))
    p("    F2-band centroid: mean=%.1fHz range=%.1fHz std=%.2fHz" % (
        float(np.mean(c2s)), float(np.max(c2s) - np.min(c2s)), float(np.std(c2s))))

    # (e-solo) microprosody: linear-detrended F0 residual on the flat-ish seg1
    win3, hop3 = int(0.020 * SR), int(0.010 * SR)
    ts3, fs3 = [], []
    for s in range(0, len(steady) - win3, hop3):
        f, pkv = autocorr_f0_peak(steady[s:s + win3])
        if np.isfinite(f):
            ts3.append(s / SR)
            fs3.append(f)
    ts3, fs3 = np.array(ts3), np.array(fs3)
    st3 = 12.0 * np.log2(fs3 / 120.0)
    A = np.vstack([ts3, np.ones_like(ts3)]).T
    coef, _, _, _ = np.linalg.lstsq(A, st3, rcond=None)
    r3 = st3 - (coef[0] * ts3 + coef[1])
    p("(e-solo) seg1 F0 linear-detrended residual: std=%.4f st slope=%.4f st/s (n=%d)" % (
        float(np.std(r3)), float(coef[0]), len(r3)))

    # (d2) within-segment drift on demo final vowels via replicated Korean plan bounds
    M64 = (1 << 64) - 1

    def splitmix64(x):
        x = (x + 0x9E3779B97F4A7C15) & M64
        z = x
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M64
        return z ^ (z >> 31)

    def variance(i):
        return 1.0 + 0.12 * (splitmix64(i ^ 0x9E3779B97F4A7C15) / float(1 << 64) - 0.5)

    KUNITS = {
        "annyeong": [("a", 180.0, True), ("n", 90.0, False), ("n", 90.0, False), ("j", 90.0, False),
                     ("V", 155.0, True), ("N", 90.0, False), ("h\\", 110.0, False), ("a", 180.0, True),
                     ("s", 130.0, False), ("e", 160.0, True), ("j", 90.0, False), ("o", 160.0, True)],
        "yeobo": [("j", 90.0, False), ("V", 155.0, True), ("b", 90.0, False), ("o", 160.0, True),
                  ("s", 130.0, False), ("e", 160.0, True), ("j", 90.0, False), ("o", 160.0, True)],
    }
    KWORD = {"annyeong": [1, 1, 3], "yeobo": [4]}
    KWN = {((1, 1, 3), 0): 2, ((1, 1, 3), 1): 4, ((1, 1, 3), 2): 6, ((4,), 0): 8}

    def plan_bounds(label):
        units = KUNITS[label]
        word_syl = KWORD[label]

        def ufw(wi):
            off = sum(KWN[(tuple(word_syl), w)] for w in range(wi))
            return units[off:off + KWN[(tuple(word_syl), wi)]]

        durs = []
        fi = 0
        for wi, nsyl in enumerate(word_syl):
            chunk = ufw(wi)
            last_v = max(i for i, (_, _, vv) in enumerate(chunk) if vv)
            for k, (sym, base, isv) in enumerate(chunk):
                ctx = 1.0
                if isv or sym in ("n", "N", "j"):
                    nxt = chunk[k + 1][0] if k + 1 < len(chunk) else None
                    if nxt is None and wi + 1 < len(word_syl):
                        nxt = ufw(wi + 1)[0][0]
                    if nxt in ("s", "k", "t", "p", "h"):
                        ctx = 0.78
                poly = 1.0 if nsyl <= 1 else (0.9 if nsyl == 2 else 0.8)
                cluster = 0.8 if (not isv and fi > 0 and not units[fi - 1][2]) else 1.0
                initial = 1.1 if (k == 0 and not isv) else 1.0
                final = 1.6 if (wi == len(word_syl) - 1 and k >= last_v) else 1.0
                floor = 40.0 if isv else (50.0 if sym in ("s", "h\\") else 30.0)
                ms = round(max(base * ctx * poly * cluster * final * initial * variance(fi), floor))
                durs.append(ms)
                fi += 1
        short = int(0.008 * SR)
        bounds, acc = [0], 0
        for i, ms in enumerate(durs):
            nn_ = max(1, int(round(ms / 1000.0 * SR)))
            if i > 0:
                acc -= min(short, acc)
            acc += nn_
            bounds.append(acc)
        return bounds, durs

    def drift_track(x, b0, b1, f1b, f2b, tag, p):
        frames = []
        s = b0 + int(0.030 * SR)
        end = b1 - int(0.040 * SR)
        while s + int(0.030 * SR) <= end:
            frames.append(x[s:s + int(0.030 * SR)])
            s += int(0.030 * SR)
        f1s, f2s, c1s, c2s = [], [], [], []
        for seg in frames:
            m = 4096
            w = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(len(seg)) / len(seg))
            pw = np.abs(np.fft.rfft(seg * w, n=m)) ** 2
            fr = np.fft.rfftfreq(m, 1.0 / SR)
            for flo, fhi, store in ((f1b[0], f1b[1], f1s), (f2b[0], f2b[1], f2s)):
                lo = int(np.searchsorted(fr, flo))
                hi = int(np.searchsorted(fr, fhi))
                k = lo + int(np.argmax(pw[lo:hi]))
                if 0 < k < len(pw) - 1 and pw[k] > 0:
                    dd = 0.5 * (pw[k - 1] - pw[k + 1]) / (pw[k - 1] - 2 * pw[k] + pw[k + 1] + 1e-18)
                    dd = float(np.clip(dd, -0.5, 0.5))
                    store.append(float(fr[k] + dd * (fr[1] - fr[0])))
                else:
                    store.append(float(fr[k]))
            bb1 = (fr >= f1b[0]) & (fr <= f1b[1])
            bb2 = (fr >= f2b[0]) & (fr <= f2b[1])
            c1s.append(float((fr[bb1] * pw[bb1]).sum() / max(pw[bb1].sum(), 1e-18)))
            c2s.append(float((fr[bb2] * pw[bb2]).sum() / max(pw[bb2].sum(), 1e-18)))
        p("(d2) %s nframes=%d: F1cent range=%.1fHz std=%.2f | F2cent range=%.1fHz std=%.2f" % (
            tag, len(frames), float(np.max(c1s) - np.min(c1s)), float(np.std(c1s)),
            float(np.max(c2s) - np.min(c2s)), float(np.std(c2s))))
        p("(d2) %s: F1peak range=%.1fHz std=%.2f | F2peak range=%.1fHz std=%.2f" % (
            tag, float(np.max(f1s) - np.min(f1s)), float(np.std(f1s)),
            float(np.max(f2s) - np.min(f2s)), float(np.std(f2s))))

    for label, path in [("annyeong", PROBE + "/fresh_annyeong.wav"),
                        ("yeobo", PROBE + "/fresh_yeobo.wav")]:
        _, nn_, xx = load(path)
        bounds, durs = plan_bounds(label)
        p("(d2) %s planned total=%d render=%d drift=%d final-o [%d,%d)" % (
            label, bounds[-1], nn_, bounds[-1] - nn_, bounds[-2], bounds[-1]))
        drift_track(xx, bounds[-2], min(bounds[-1], nn_), (300.0, 700.0), (600.0, 1500.0),
                    label + " final-o", p)

    # (e) residual F0 on demos after 200ms median detrend
    p("(e) demo residual F0 (20ms win / 10ms hop, 200ms median detrend):")
    for label, path in [("hello", PROBE + "/fresh_hello.wav"),
                        ("annyeong", PROBE + "/fresh_annyeong.wav"),
                        ("yeobo", PROBE + "/fresh_yeobo.wav")]:
        _, nn, xx = load(path)
        win2, hop2 = int(0.020 * SR), int(0.010 * SR)
        ts, fs = [], []
        for s in range(0, nn - win2, hop2):
            f, pkv = autocorr_f0_peak(xx[s:s + win2], 60.0, 300.0)
            if np.isfinite(f) and pkv > 0.35:
                ts.append(s / SR)
                fs.append(f)
        fs = np.array(fs)
        st = 12.0 * np.log2(fs / 120.0)
        med = np.array([np.median(st[max(0, i - 10):i + 11]) for i in range(len(st))])
        resid_st = st - med
        p("    %s: voiced frames %d/%d, residual std=%.4f st, max|resid|=%.4f st" % (
            label, len(fs), (nn - win2) // hop2, float(np.std(resid_st)),
            float(np.max(np.abs(resid_st)))))
        f5 = np.sort(fs)
        p("    %s: F0 p5=%.1f p50=%.1f p95=%.1f Hz" % (
            label, f5[int(0.05 * len(f5))], f5[len(f5) // 2], f5[int(0.95 * len(f5))]))

    open(LOGDIR + "/probe.log", "w").write("\n".join(lines) + "\n")
    p("transcript saved to %s/probe.log" % LOGDIR)


main()
