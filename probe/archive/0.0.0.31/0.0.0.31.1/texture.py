# Background texture probe for task 0.0.0.31.1 (read-only, no engine change).
# Per VOICED segment interior (10 ms edges excluded):
#  (a) voicing depth = peak normalized autocorrelation in 80-300 Hz lag band.
#  (b) noise-floor RMS = RMS of residual after subtracting a harmonic comb
#      pitched at the lag of (a): p[i] = 0.5*(x[i-L]+x[i+L]).
#      Cross-check proxy: HP(4k brickwall via rfft) RMS.
#  (c) spectral tilt = 10*log10(E[0-1kHz] / E[4kHz+]) and HF fraction E[4k+]/E[tot].
# Across-segment variance (the "different rooms" number): CV = std/mean of
# voicing depth, noise floor, HF fraction; std of tilt (dB scale).
# Fricatives (/h/ frication path, /s/ parallel sibilant) and /b/ burst are
# measured as REFERENCE rows and excluded from the variance verdict.
# Segment output ranges replicate the engine concat arithmetic exactly
# (work-unit lens minus 176-sample fades), parsed from plan.txt dumped by the
# 0.0.0.24.1 plandump; predicted totals match wav lengths exactly.
# GOAT-merged hello o+U work unit is split at first seglen (3263 samples).

import re
import struct
import wave
import numpy as np

SR = 22050
EDGE = int(0.010 * SR)  # 10 ms = 220.5 -> 221
LAG_LO = int(round(SR / 300.0))  # 73
LAG_HI = int(round(SR / 80.0))   # 276

LABELS = {
    "hello": ["h", "E", "l", "o", "U"],
    "annyeong": ["a", "n", "n", "j", "V", "N", "h", "a", "s", "e", "j", "o"],
    "yeobo": ["j", "V", "b", "o", "s", "e", "j", "o"],
}
# design class: V = vowel, S = sonorant (periodic by design -> verdict set),
# F = fricative-path reference, P = plosive (burst envelope, reference)
CLASS = {
    "hello": ["F", "V", "S", "V", "V"],
    "annyeong": ["V", "S", "S", "S", "V", "S", "F", "V", "F", "V", "S", "V"],
    "yeobo": ["S", "V", "P", "V", "F", "V", "S", "V"],
}
# creak excitation per synth.rs:483-487 (final + voiced + not frication/mixed +
# not(short + follows_goat_onset)); hello U is short and follows stressed o
# (is_goat_onset: synth.rs:130-135) so modal; annyeong/yeobo final o creak.
CREAK = {
    "hello": [False, False, False, False, False],
    "annyeong": [False] * 11 + [True],
    "yeobo": [False] * 7 + [True],
}


def load_wav(path):
    with wave.open(path, "rb") as w:
        n = w.getnframes()
        data = w.readframes(n)
    x = np.array(struct.unpack("<%dh" % n, data), dtype=np.float64) / 32767.0
    return x


def parse_plan(path):
    utts = {}
    cur = None
    for line in open(path, encoding="utf-8"):
        m = re.match(r"== (\w+) ::", line)
        if m:
            cur = m.group(1)
            utts[cur] = {"units": [], "lens": None, "fades": None}
            continue
        m = re.match(r"u(\d+) sym=(\S+) dur=(\d+)ms.*spec=(\w+) seglen=(\d+) gain=([-\d.]+)dB", line)
        if m and cur:
            utts[cur]["units"].append({
                "sym": m.group(2), "dur": int(m.group(3)), "spec": m.group(4),
                "seglen": int(m.group(5)), "gain": float(m.group(6)),
            })
        m = re.match(r"work_units=(.*) lens=\[(.*)\] fades=\[(.*)\]", line)
        if m and cur:
            utts[cur]["lens"] = [int(v) for v in m.group(2).split(",")]
            utts[cur]["fades"] = [int(v) for v in m.group(3).split(",")]
            wus = re.findall(r"\[(.*?)\]", m.group(1))
            utts[cur]["wus"] = [[int(v) for v in w.split(",") if v.strip() != ""]
                                for w in wus]
    return utts


def output_ranges(utt):
    # start[i] of work unit i = sum(lens[:i]) - 176*i (fades all 176 except 0)
    lens, fades, wus = utt["lens"], utt["fades"], utt["wus"]
    ranges = {}  # unit idx -> (start, end)
    pos = 0
    for wi, wu in enumerate(wus):
        ln = lens[wi]
        start = pos - (fades[wi] if wi > 0 else 0)
        for k, u in enumerate(wu):
            if len(wu) == 1:
                ranges[u] = (start, start + ln)
            else:
                # GOAT merge: split proportionally to seglen (hello o+U:
                # 3263+1830 = 5093 vs work len 5094, 1-sample slack on 2nd)
                segs = [utt["units"][j]["seglen"] for j in wu]
                off = 0
                for j, s in zip(wu, segs):
                    if j == u:
                        end = start + ln if j == wu[-1] else start + off + s
                        ranges[u] = (start + off, end)
                    off += s
        pos = start + ln
    return ranges, pos


def autocorr_peak(x):
    e = np.dot(x, x)
    if e <= 0:
        return 0.0, LAG_LO
    n = len(x)
    best, bl = -1.0, LAG_LO
    for lag in range(LAG_LO, min(LAG_HI, n // 2) + 1):
        r = np.dot(x[:n - lag], x[lag:]) / e
        if r > best:
            best, bl = r, lag
    return best, bl


def analyze_seg(x):
    n = len(x)
    depth, lag = autocorr_peak(x)
    # harmonic-comb residual
    if n > 2 * lag:
        core = x[lag:n - lag]
        pred = 0.5 * (x[:n - 2 * lag] + x[2 * lag:])
        resid = core - pred
        nf = float(np.sqrt(np.mean(resid ** 2)))
    else:
        nf = float(np.sqrt(np.mean(x ** 2)))
    X = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(n, 1.0 / SR)
    P = (X.real ** 2 + X.imag ** 2)
    tot = P.sum()
    e_low = P[freqs <= 1000.0].sum()
    e_high = P[freqs >= 4000.0].sum()
    hf_frac = float(e_high / tot) if tot > 0 else 0.0
    tilt = float(10 * np.log10(e_low / e_high)) if e_low > 0 and e_high > 0 else float("nan")
    # HP-proxy noise floor: brickwall above 4 kHz back to time domain
    H = np.zeros_like(X)
    H[freqs >= 4000.0] = X[freqs >= 4000.0]
    hp = np.fft.irfft(H, n=n)
    hp_rms = float(np.sqrt(np.mean(hp ** 2)))
    rms = float(np.sqrt(np.mean(x ** 2)))
    return {"depth": depth, "lag": lag, "noise_floor": nf, "hp_rms": hp_rms,
            "rms": rms, "hf_frac": hf_frac, "tilt": tilt, "n": n}


plan = parse_plan(r"E:\01_coding\ARTicul\probe\archive\0.0.0.24\0.0.0.24.1\plan.txt")
for name in ["hello", "annyeong", "yeobo"]:
    wpath = r"E:\01_coding\ARTicul\probe\0.0.0.31.1\%s.wav" % name
    x = load_wav(wpath)
    utt = plan[name]
    ranges, total = output_ranges(utt)
    print("== %s wav=%d predicted=%d %s" % (name, len(x), total,
                                            "OK" if len(x) == total else "MISMATCH"))
    print("seg sym cls creak interior_n depth lag noise_floor hp_rms rms hf_frac tilt_db")
    rows = []
    for i, u in enumerate(utt["units"]):
        s, e = ranges[i]
        a, b = s + EDGE, e - EDGE
        seg = x[a:b]
        m = analyze_seg(seg)
        rows.append(m)
        print("u%-2d %-3s %-4s %-5s %-9d %.4f %-4d %.6f %.6f %.6f %.5f %7.2f" % (
            i, LABELS[name][i], CLASS[name][i], str(CREAK[name][i]),
            len(seg), m["depth"], m["lag"], m["noise_floor"], m["hp_rms"],
            m["rms"], m["hf_frac"], m["tilt"]))
    # verdict set: voiced = V/S classes
    v = [m for i, m in enumerate(rows) if CLASS[name][i] in ("V", "S")]
    f = [m for i, m in enumerate(rows) if CLASS[name][i] == "F"]
    for key in ["depth", "noise_floor", "hp_rms", "hf_frac"]:
        vals = np.array([m[key] for m in v])
        print("VOICED %s: mean=%.6f std=%.6f CV=%.4f min=%.6f max=%.6f" % (
            key, vals.mean(), vals.std(), vals.std() / vals.mean() if vals.mean() else 0,
            vals.min(), vals.max()))
    t = np.array([m["tilt"] for m in v])
    print("VOICED tilt_db: mean=%.2f std=%.2f min=%.2f max=%.2f range=%.2f" % (
        t.mean(), t.std(), t.min(), t.max(), t.max() - t.min()))
    for key in ["hf_frac", "noise_floor", "tilt", "depth"]:
        vals = np.array([m[key] for m in f])
        print("FRIC-REF %s: %s" % (key, " ".join("%.5f" % q for q in vals)))
