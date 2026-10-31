# Frame-based refinement: split each segment interior into 40 ms frames
# (20 ms step), metric per frame, mean across frames. Removes the confound of
# slow intra-segment F0 glides (hello o 155->80 Hz, annyeong a 158->135 Hz)
# that collapse whole-segment autocorrelation. Adds hp_depth = autocorr peak
# of the 4k+ brickwall HP signal: high => HF energy is harmonic (bright
# formant, filter shaping); low => HF energy is inharmonic (noise bed).

import re
import struct
import wave
import numpy as np

SR = 22050
EDGE = int(0.010 * SR)
FLEN = int(0.040 * SR)   # 882
FSTEP = int(0.020 * SR)  # 441
LAG_LO = int(round(SR / 300.0))
LAG_HI = int(round(SR / 80.0))

LABELS = {
    "hello": ["h", "E", "l", "o", "U"],
    "annyeong": ["a", "n", "n", "j", "V", "N", "h", "a", "s", "e", "j", "o"],
    "yeobo": ["j", "V", "b", "o", "s", "e", "j", "o"],
}
CLASS = {
    "hello": ["F", "V", "S", "V", "V"],
    "annyeong": ["V", "S", "S", "S", "V", "S", "F", "V", "F", "V", "S", "V"],
    "yeobo": ["S", "V", "P", "V", "F", "V", "S", "V"],
}
CREAK = {
    "hello": [False, False, False, False, False],
    "annyeong": [False] * 11 + [True],
    "yeobo": [False] * 7 + [True],
}


def load_wav(path):
    with wave.open(path, "rb") as w:
        n = w.getnframes()
        data = w.readframes(n)
    return np.array(struct.unpack("<%dh" % n, data), dtype=np.float64) / 32767.0


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
    lens, fades, wus = utt["lens"], utt["fades"], utt["wus"]
    ranges = {}
    pos = 0
    for wi, wu in enumerate(wus):
        ln = lens[wi]
        start = pos - (fades[wi] if wi > 0 else 0)
        if len(wu) == 1:
            ranges[wu[0]] = (start, start + ln)
        else:
            off = 0
            for j in wu:
                s = utt["units"][j]["seglen"]
                end = start + ln if j == wu[-1] else start + off + s
                ranges[j] = (start + off, end)
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


def hp4k(x):
    n = len(x)
    X = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(n, 1.0 / SR)
    H = np.zeros_like(X)
    H[freqs >= 4000.0] = X[freqs >= 4000.0]
    return np.fft.irfft(H, n=n)


def frame_metrics(fr):
    depth, lag = autocorr_peak(fr)
    n = len(fr)
    if n > 2 * lag:
        core = fr[lag:n - lag]
        pred = 0.5 * (fr[:n - 2 * lag] + fr[2 * lag:])
        nf = float(np.sqrt(np.mean((core - pred) ** 2)))
    else:
        nf = float(np.sqrt(np.mean(fr ** 2)))
    hp = hp4k(fr)
    hp_rms = float(np.sqrt(np.mean(hp ** 2)))
    hp_depth, _ = autocorr_peak(hp)
    X = np.fft.rfft(fr)
    freqs = np.fft.rfftfreq(n, 1.0 / SR)
    P = X.real ** 2 + X.imag ** 2
    tot = P.sum()
    e_low = P[freqs <= 1000.0].sum()
    e_high = P[freqs >= 4000.0].sum()
    hf_frac = float(e_high / tot) if tot > 0 else 0.0
    tilt = float(10 * np.log10(e_low / e_high)) if e_low > 0 and e_high > 0 else float("nan")
    rms = float(np.sqrt(np.mean(fr ** 2)))
    return {"depth": depth, "noise_floor": nf, "hp_rms": hp_rms,
            "hp_depth": hp_depth, "hf_frac": hf_frac, "tilt": tilt, "rms": rms}


plan = parse_plan(r"E:\01_coding\ARTicul\probe\archive\0.0.0.24\0.0.0.24.1\plan.txt")
for name in ["hello", "annyeong", "yeobo"]:
    x = load_wav(r"E:\01_coding\ARTicul\probe\0.0.0.31.1\%s.wav" % name)
    utt = plan[name]
    ranges, total = output_ranges(utt)
    assert len(x) == total, (name, len(x), total)
    print("== %s (ranges sample-exact, total=%d)" % (name, total))
    print("seg sym cls creak nfr depth noise_floor hp_rms hp_depth hf_frac tilt_db rms")
    rows = []
    for i, u in enumerate(utt["units"]):
        s, e = ranges[i]
        seg = x[s + EDGE:e - EDGE]
        starts = list(range(0, max(1, len(seg) - FLEN + 1), FSTEP))
        if len(seg) < FLEN:
            starts = [0]
        acc = {}
        for st in starts:
            fr = seg[st:st + FLEN]
            if len(fr) < FLEN // 2:
                continue
            m = frame_metrics(fr)
            for k, v in m.items():
                acc.setdefault(k, []).append(v)
        m = {k: float(np.mean(v)) for k, v in acc.items()}
        rows.append(m)
        print("u%-2d %-3s %-4s %-5s %-3d %.4f %.6f %.6f %.4f %.5f %7.2f %.6f" % (
            i, LABELS[name][i], CLASS[name][i], str(CREAK[name][i]), len(acc["depth"]),
            m["depth"], m["noise_floor"], m["hp_rms"], m["hp_depth"],
            m["hf_frac"], m["tilt"], m["rms"]))
    v = [m for i, m in enumerate(rows) if CLASS[name][i] in ("V", "S")]
    f = [m for i, m in enumerate(rows) if CLASS[name][i] == "F"]
    for key in ["depth", "noise_floor", "hp_rms", "hp_depth", "hf_frac"]:
        vals = np.array([m[key] for m in v])
        cv = vals.std() / vals.mean() if vals.mean() else 0
        print("VOICED %s: mean=%.6f std=%.6f CV=%.4f min=%.6f max=%.6f x=%.2f" % (
            key, vals.mean(), vals.std(), cv, vals.min(), vals.max(),
            vals.max() / vals.min() if vals.min() > 0 else 0))
    t = np.array([m["tilt"] for m in v])
    print("VOICED tilt_db: mean=%.2f std=%.2f min=%.2f max=%.2f range=%.2f" % (
        t.mean(), t.std(), t.min(), t.max(), t.max() - t.min()))
    for key in ["hf_frac", "hp_depth", "noise_floor", "tilt", "depth"]:
        print("FRIC-REF %s: %s" % (key, " ".join("%.5f" % m[key] for m in f)))
