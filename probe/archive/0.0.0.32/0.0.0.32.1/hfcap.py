 # HF-cap feasibility simulation for task 0.0.0.32.1 (read-only, no engine change).
# Ideal per-segment HF limiter: for each NON-FRICATIVE voiced segment, scale
# its 4kHz+ band so its HF mean-square <= K * utterance-median voiced HF
# mean-square. Fricatives (/s/, /h/) and the /b/ burst are untouched (gain 1).
# Band split is a whole-utterance FFT brickwall (ideal, zero edge artifacts);
# per-sample gain track with raised-cosine smoothing across engine blend zones
# (176 samples) and the GOAT internal edge (110 samples).
# Metrics per K in {1.5, 2.0, 3.0, 4.0}:
#  (a) voiced HF-fraction max/min ratio (whole-interior FFT, texture.py method)
#  (b) sibilant HF preservation (dB change on /s/ interiors)
#  (c) lateral notch depth on hello 170-210ms window (0.0.0.20.2 metric)
#  (d) per-demo broadband RMS delta vs baseline

import re
import math
import struct
import wave
import numpy as np

SR = 22050
EDGE = int(0.010 * SR)
CUTOFF = 4000.0
KS = [1.5, 2.0, 3.0, 4.0]
ROOT = r"E:\01_coding\ARTicul"
PLAN = ROOT + r"\probe\archive\0.0.0.24\0.0.0.24.1\plan.txt"

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
NOTCH_WIN = (int(0.170 * SR), int(0.210 * SR))  # 3748..4630
GOAT_SMOOTH = 110  # samples, total width across GOAT internal edge


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
            utts[cur] = {"units": [], "lens": None, "fades": None,
                         "wus": None, "zones": []}
            continue
        m = re.match(r"u(\d+) sym=(\S+) dur=(\d+)ms.*spec=(\w+) seglen=(\d+) gain=([-\d.]+)dB", line)
        if m and cur:
            utts[cur]["units"].append({"sym": m.group(2), "dur": int(m.group(3)),
                                       "spec": m.group(4), "seglen": int(m.group(5))})
        m = re.match(r"work_units=(.*) lens=\[(.*)\] fades=\[(.*)\]", line)
        if m and cur:
            utts[cur]["lens"] = [int(v) for v in m.group(2).split(",")]
            utts[cur]["fades"] = [int(v) for v in m.group(3).split(",")]
            wus = re.findall(r"\[(.*?)\]", m.group(1))
            utts[cur]["wus"] = [[int(v) for v in w.split(",") if v.strip() != ""]
                                for w in wus]
        m = re.match(r"b\d+ between u(\d+)\(.*\)->u(\d+)\(.*\) type=(\S+) zone=\[(\d+), (\d+)\)", line)
        if m and cur:
            utts[cur]["zones"].append({"prev": int(m.group(1)), "next": int(m.group(2)),
                                      "z0": int(m.group(4)), "z1": int(m.group(5))})
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
            segs = [utt["units"][j]["seglen"] for j in wu]
            off = 0
            for j, s in zip(wu, segs):
                end = start + ln if j == wu[-1] else start + off + s
                ranges[j] = (start + off, end)
                off += s
        pos = start + ln
    return ranges, pos


def split_hp(x, cutoff=CUTOFF):
    n = len(x)
    X = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(n, 1.0 / SR)
    H = np.zeros_like(X)
    H[freqs >= cutoff] = X[freqs >= cutoff]
    hf = np.fft.irfft(H, n=n)
    return x - hf, hf


def hf_frac_interior(x, a, b):
    seg = x[a:b]
    n = len(seg)
    X = np.fft.rfft(seg)
    freqs = np.fft.rfftfreq(n, 1.0 / SR)
    P = X.real ** 2 + X.imag ** 2
    tot = P.sum()
    e_high = P[freqs >= CUTOFF].sum()
    return float(e_high / tot) if tot > 0 else 0.0, float(e_high), float(tot)


FR_LEN = int(0.020 * SR)  # 441 samples
FR_STEP = int(0.010 * SR)  # 220 samples


def frame_mean_frac(x, a, b, cutoff=CUTOFF):
    n = len(x)
    X = None
    fs = []
    p = a
    while p + FR_LEN <= b:
        seg = x[p:p + FR_LEN]
        X = np.fft.rfft(seg)
        freqs = np.fft.rfftfreq(FR_LEN, 1.0 / SR)
        P = X.real ** 2 + X.imag ** 2
        tot = P.sum()
        fs.append(float(P[freqs >= cutoff].sum() / tot) if tot > 0 else 0.0)
        p += FR_STEP
    if not fs:  # interior shorter than one frame: single whole-interior estimate
        seg = x[a:b]
        X = np.fft.rfft(seg)
        freqs = np.fft.rfftfreq(len(seg), 1.0 / SR)
        P = X.real ** 2 + X.imag ** 2
        tot = P.sum()
        fs.append(float(P[freqs >= cutoff].sum() / tot) if tot > 0 else 0.0)
    return float(np.mean(fs)), len(fs)


def notch_depth(x, a, b, n_fft=8192):
    w = x[a:b] * np.hanning(b - a)
    X = np.fft.rfft(w, n=n_fft)
    P = X.real ** 2 + X.imag ** 2
    freqs = np.fft.rfftfreq(n_fft, 1.0 / SR)
    core = P[(freqs >= 2470.0) & (freqs <= 2530.0)]
    flank = P[(freqs >= 2000.0) & (freqs <= 2300.0)]
    return float(10 * np.log10(np.median(flank) / np.median(core)))


def build_track(n, ranges, nunits, gains, zones, goat_splits):
    units_of = {}
    for i in range(nunits):
        s, e = ranges[i]
        units_of[i] = (s, e)
    cuts = sorted(set([0, n] + [z["z0"] for z in zones] + [z["z1"] for z in zones]
                      + goat_splits))
    track = np.ones(n)
    for m in range(len(cuts) - 1):
        c0, c1 = cuts[m], cuts[m + 1]
        if c1 <= c0:
            continue
        mid = (c0 + c1) // 2
        owner = None
        for i in range(nunits):
            s, e = units_of[i]
            if s <= mid < e:
                owner = i
                break
        if owner is None:
            owner = nunits - 1
        track[c0:c1] = gains[owner]
    for z in zones:
        z0, z1 = z["z0"], z["z1"]
        g0 = track[z0 - 1] if z0 > 0 else gains[z["prev"]]
        g1 = track[z1] if z1 < n else gains[z["next"]]
        t = np.arange(z1 - z0) / float(z1 - z0)
        w = 0.5 - 0.5 * np.cos(np.pi * t)
        track[z0:z1] = g0 * (1 - w) + g1 * w
    for gs in goat_splits:
        a0 = max(0, gs - GOAT_SMOOTH // 2)
        a1 = min(n, gs + GOAT_SMOOTH // 2)
        g0 = track[a0]
        g1 = track[a1 - 1]
        t = np.arange(a1 - a0) / float(a1 - a0)
        w = 0.5 - 0.5 * np.cos(np.pi * t)
        track[a0:a1] = g0 * (1 - w) + g1 * w
    return track


def voiced_idx(name):
    return [i for i, c in enumerate(CLASS[name]) if c in ("V", "S")]


def simulate(x, ranges, nunits, vset, K, zones, goat_splits, cutoff=CUTOFF):
    _, hf = split_hp(x, cutoff)
    ms = {}
    for i in vset:
        s, e = ranges[i]
        seg = hf[s + EDGE:e - EDGE]
        ms[i] = float(np.mean(seg ** 2))
    med = float(np.median([ms[i] for i in vset]))
    cap = K * med
    gains = np.ones(nunits)
    for i in vset:
        gains[i] = min(1.0, float(np.sqrt(cap / ms[i]))) if ms[i] > 0 else 1.0
    track = build_track(len(x), ranges, nunits, gains, zones, goat_splits)
    lf = x - hf
    y = lf + track * hf
    return y, gains, med, ms


plan = parse_plan(PLAN)
data = {}
out_lines = []
for name in ["hello", "annyeong", "yeobo"]:
    x = load_wav(ROOT + r"\probe\0.0.0.32.1\%s.wav" % name)
    utt = plan[name]
    ranges, total = output_ranges(utt)
    assert len(x) == total, (name, len(x), total)
    goat_splits = []
    for wi, wu in enumerate(utt["wus"]):
        if len(wu) > 1:
            s = ranges[wu[0]][0]
            off = 0
            for j in wu[:-1]:
                off += utt["units"][j]["seglen"]
                goat_splits.append(s + off)
    data[name] = {"x": x, "utt": utt, "ranges": ranges, "total": total,
                  "goat": goat_splits, "vset": voiced_idx(name),
                  "nunits": len(utt["units"])}

# lossless control: all-ones track reproduces input
ctrl_max = 0.0
for name in data:
    d = data[name]
    n = len(d["x"])
    tr = build_track(n, d["ranges"], d["nunits"], np.ones(d["nunits"]),
                     d["utt"]["zones"], d["goat"])
    ctrl_max = max(ctrl_max, float(np.max(np.abs(tr - 1.0))))
_, hf_chk = split_hp(data["hello"]["x"])
rec = (data["hello"]["x"] - hf_chk) + 1.0 * hf_chk
rec_err = float(np.sqrt(np.mean((rec - data["hello"]["x"]) ** 2)))
out_lines.append("lossless control: max|track-1| = %.3e, split/recombine RMS residual = %.3e"
                 % (ctrl_max, rec_err))

# baseline metrics (a = whole-interior HF-fraction ratio, texture 0.0.0.31.1 method)
base = {}
for name in data:
    d = data[name]
    x = d["x"]
    fr = {}
    for i in d["vset"]:
        s, e = d["ranges"][i]
        f, _, _ = hf_frac_interior(x, s + EDGE, e - EDGE)
        fr[i] = f
    vals = np.array(list(fr.values()))
    base[name] = {"fr": fr, "ratio": float(vals.max() / vals.min()),
                  "rms": float(np.sqrt(np.mean(x ** 2))),
                  "notch": notch_depth(x, *NOTCH_WIN) if name == "hello" else None}
    out_lines.append("baseline %s: voiced HF-fraction max/min = %.4f (max=%.5f min=%.5f) rms=%.6f%s"
                     % (name, base[name]["ratio"], vals.max(), vals.min(),
                        base[name]["rms"],
                        " notch=%.2fdB" % base[name]["notch"] if name == "hello" else ""))

results = {}
for K in KS:
    results[K] = {}
    for name in data:
        d = data[name]
        y, gains, med, ms = simulate(d["x"], d["ranges"], d["nunits"], d["vset"],
                                     K, d["utt"]["zones"], d["goat"])
        fr = {}
        for i in d["vset"]:
            s, e = d["ranges"][i]
            f, _, _ = hf_frac_interior(y, s + EDGE, e - EDGE)
            fr[i] = f
        vals = np.array(list(fr.values()))
        rms = float(np.sqrt(np.mean(y ** 2)))
        r = {"fr": fr, "ratio": float(vals.max() / vals.min()),
             "rms_db": float(20 * np.log10(rms / base[name]["rms"])),
             "gains": dict(enumerate(gains)), "med": med, "y": y}
        if name == "hello":
            r["notch"] = notch_depth(y, *NOTCH_WIN)
            r["notch_delta"] = r["notch"] - base[name]["notch"]
        # sibilant / fricative preservation on interiors
        pres = {}
        for i, c in enumerate(CLASS[name]):
            if c == "F" or LABELS[name][i] == "b":
                s, e = d["ranges"][i]
                _, eh0, _ = hf_frac_interior(d["x"], s + EDGE, e - EDGE)
                _, eh1, _ = hf_frac_interior(y, s + EDGE, e - EDGE)
                pres[LABELS[name][i] + str(i)] = float(10 * np.log10(eh1 / eh0)) if eh0 > 0 else 0.0
        r["pres"] = pres
        results[K][name] = r
        capped = [i for i in d["vset"] if gains[i] < 1.0 - 1e-12]
        out_lines.append("K=%.1f %s: ratio=%.4f rms_delta=%+.4fdB capped=%s gains=%s"
                         % (K, name, r["ratio"], r["rms_db"], capped,
                            ",".join("%.3f" % gains[i] for i in range(d["nunits"]))))
        if name == "hello":
            out_lines.append("  notch: base=%.2f sim=%.2f delta=%+.4f dB"
                             % (base[name]["notch"], r["notch"], r["notch_delta"]))
        out_lines.append("  fricative HF preservation dB: "
                         + " ".join("%s=%+.4f" % kv for kv in sorted(r["pres"].items())))
# cutoff sensitivity: rerun full sim at 3.5k / 4.5k with matching metric
# cutoff, watch (a) ratio movement (whole-interior method throughout)
sens = {}
for cut in [3500.0, 4500.0]:
    for K in KS:
        for name in data:
            d = data[name]
            y, _, _, _ = simulate(d["x"], d["ranges"], d["nunits"], d["vset"],
                                  K, d["utt"]["zones"], d["goat"], cutoff=cut)
            fr = []
            for i in d["vset"]:
                s, e = d["ranges"][i]
                seg = y[s + EDGE:e - EDGE]
                n = len(seg)
                X = np.fft.rfft(seg)
                freqs = np.fft.rfftfreq(n, 1.0 / SR)
                P = X.real ** 2 + X.imag ** 2
                tot = P.sum()
                fr.append(float(P[freqs >= cut].sum() / tot) if tot > 0 else 0.0)
            fr = np.array(fr)
            sens[(cut, K, name)] = float(fr.max() / fr.min())
sens_max = 0.0
for K in KS:
    for name in data:
        for cut in [3500.0, 4500.0]:
            sens_max = max(sens_max, abs(sens[(cut, K, name)] - results[K][name]["ratio"]))
out_lines.append("cutoff sensitivity (3.5k/4.5k, whole-interior): max |dratio| = %.4f" % sens_max)
out_lines.append("robustness table (a) ratio at 3.5k / 4.0k / 4.5k cutoffs:")
for K in KS:
    row = []
    for name in data:
        row.append("%s:%.2f/%.2f/%.2f" % (name, sens[(3500.0, K, name)],
                                          results[K][name]["ratio"], sens[(4500.0, K, name)]))
    out_lines.append("  K=%.1f %s" % (K, " ".join(row)))
# frame-mean variant (20ms/10ms, texture-header family) at 4k: method robustness
out_lines.append("frame-mean variant (20ms/10ms rect, cutoff 4k):")
for K in [1.5, 4.0]:
    row = []
    for name in data:
        d = data[name]
        y = results[K][name]["y"] if K in results else data[name]["x"]
        fr = []
        for i in d["vset"]:
            s, e = d["ranges"][i]
            f, _ = frame_mean_frac(y, s + EDGE, e - EDGE)
            fr.append(f)
        fr = np.array(fr)
        row.append("%s:%.2f" % (name, float(fr.max() / fr.min())))
    out_lines.append("  K=%.1f %s" % (K, " ".join(row)))
row = []
for name in data:
    d = data[name]
    fr = []
    for i in d["vset"]:
        s, e = d["ranges"][i]
        f, _ = frame_mean_frac(d["x"], s + EDGE, e - EDGE)
        fr.append(f)
    fr = np.array(fr)
    row.append("%s:%.2f" % (name, float(fr.max() / fr.min())))
out_lines.append("  base %s" % " ".join(row))
# determinism: rerun K=1.5 hello, must reproduce ratio bit-exactly
d = data["hello"]
y1, _, _, _ = simulate(d["x"], d["ranges"], d["nunits"], d["vset"],
                       1.5, d["utt"]["zones"], d["goat"])
fr = []
for i in d["vset"]:
    s, e = d["ranges"][i]
    f, _, _ = hf_frac_interior(y1, s + EDGE, e - EDGE)
    fr.append(f)
fr = np.array(fr)
det = abs(float(fr.max() / fr.min()) - results[1.5]["hello"]["ratio"])
out_lines.append("determinism rerun (K=1.5 hello): |dratio| = %.3e" % det)
U_A = 0.1
out_lines.append("simulator numerical bound: u_a = %.1f (determinism %.1e + frame-grid discretization; smoothing zones excluded from interiors by construction)"
                 % (U_A, det))
# smoothing cost: sharp track (no ramps) vs smoothed track RMS difference
u_smooth = 0.0
for K in KS:
    for name in data:
        d = data[name]
        y_sm = results[K][name]["y"]
        _, hf = split_hp(d["x"])
        lf = d["x"] - hf
        _, gains, _, _ = simulate(d["x"], d["ranges"], d["nunits"], d["vset"],
                                  K, d["utt"]["zones"], d["goat"])
        n = len(d["x"])
        cuts = sorted(set([0, n] + [z["z0"] for z in d["utt"]["zones"]]
                          + [z["z1"] for z in d["utt"]["zones"]] + d["goat"]))
        sharp = np.ones(n)
        for m in range(len(cuts) - 1):
            c0, c1 = cuts[m], cuts[m + 1]
            if c1 <= c0:
                continue
            mid = (c0 + c1) // 2
            owner = d["nunits"] - 1
            for i in range(d["nunits"]):
                s, e = d["ranges"][i]
                if s <= mid < e:
                    owner = i
                    break
            sharp[c0:c1] = gains[owner]
        y_sh = lf + sharp * hf
        dd = abs(float(20 * np.log10(np.sqrt(np.mean(y_sm ** 2)) / np.sqrt(np.mean(y_sh ** 2)))))
        u_smooth = max(u_smooth, dd)
u_d = max(0.01, math.ceil(u_smooth * 1000) / 1000.0 * 2)
out_lines.append("smoothing cost: max |rms_smooth - rms_sharp| = %.5fdB -> u_d = %.3fdB"
                 % (u_smooth, u_d))
# total-energy-median variant (sensitivity): cap on total HF energy, K=1.5
out_lines.append("--- total-energy-median variant (sensitivity, K=1.5) ---")
for name in data:
    d = data[name]
    _, hf = split_hp(d["x"])
    tot_e = {}
    for i in d["vset"]:
        s, e = d["ranges"][i]
        seg = hf[s + EDGE:e - EDGE]
        tot_e[i] = float(np.sum(seg ** 2))
    med_e = float(np.median(list(tot_e.values())))
    cap_e = 1.5 * med_e
    gains = np.ones(d["nunits"])
    for i in d["vset"]:
        gains[i] = min(1.0, float(np.sqrt(cap_e / tot_e[i]))) if tot_e[i] > 0 else 1.0
    track = build_track(len(d["x"]), d["ranges"], d["nunits"], gains,
                        d["utt"]["zones"], d["goat"])
    y = (d["x"] - hf) + track * hf
    fr = []
    for i in d["vset"]:
        s, e = d["ranges"][i]
        f, _, _ = hf_frac_interior(y, s + EDGE, e - EDGE)
        fr.append(f)
    fr = np.array(fr)
    out_lines.append("%s: MS-variant ratio=%.4f totalE-variant ratio=%.4f capped=%s"
                     % (name, results[1.5][name]["ratio"], float(fr.max() / fr.min()),
                        [i for i in d["vset"] if gains[i] < 1.0 - 1e-12]))
# verdict with 2x margins
A_T, B_T, C_T, D_T = 3.0, 0.5, 6.0, 1.0
U_B, U_C = 0.01, 0.05
u_ratio = U_A
out_lines.append("--- verdict (2x-margin acceptance) ---")
out_lines.append("bounds: u_ratio=%.1f u_b=%.2f u_c=%.2f u_d=%.3f" % (u_ratio, U_B, U_C, u_d))
out_lines.append("accept: (a) sim+2u<=%.1f | (b) |sim|+2u<=%.1f | (c) sim-2u>=%.1f | (d) |sim|+2u<=%.1f"
                 % (A_T, B_T, C_T, D_T))
binding = []
passing = []
for K in KS:
    cells = []
    for name in data:
        r = results[K][name]
        a_ok = (r["ratio"] + 2 * u_ratio) <= A_T
        d_ok = (abs(r["rms_db"]) + 2 * u_d) <= D_T
        cells.append((name, a_ok, d_ok))
        if not a_ok:
            binding.append("K=%.1f %s (a) ratio %.2f + 2u(%.1f) = %.2f > 3.0"
                           % (K, name, r["ratio"], u_ratio, r["ratio"] + 2 * u_ratio))
        if not d_ok:
            binding.append("K=%.1f %s (d) |rms| %.4f + 2u(%.3f) > 1.0" % (K, name, abs(r["rms_db"]), u_d))
    b_ok = True
    for name in data:
        for k, v in results[K][name]["pres"].items():
            if k.startswith("s") and abs(v) + 2 * U_B > B_T:
                b_ok = False
                binding.append("K=%.1f %s (b) %s %+.4f out of bound" % (K, name, k, v))
    c = results[K]["hello"]
    c_ok = (c["notch"] - 2 * U_C) >= C_T
    if not c_ok:
        binding.append("K=%.1f hello (c) notch %.2f - 2u < 6.0" % (K, c["notch"]))
    allok = all(a and d for _, a, d in cells) and b_ok and c_ok
    if allok:
        passing.append(K)
    out_lines.append("K=%.1f: (a) %s (b) %s (c) %s (d) %s => %s"
                     % (K, ",".join("%s:%s" % (n, "PASS" if a else "FAIL") for n, a, _ in cells),
                        "PASS" if b_ok else "FAIL", "PASS" if c_ok else "FAIL",
                        ",".join("%s:%s" % (n, "PASS" if dd else "FAIL") for n, _, dd in cells),
                        "PASS" if allok else "FAIL"))
if passing:
    out_lines.append("VERDICT: PASS at K=%s" % passing)
else:
    out_lines.append("VERDICT: NO-PASSING-POINT (%d binding cells):" % len(binding))
    out_lines.extend("  BINDING: " + b for b in binding)
report = "\n".join(out_lines) + "\n"
print(report, end="")
open(ROOT + r"\probe\0.0.0.32.1\hfcap.txt", "w", encoding="utf-8").write(
    "0.0.0.32.1 HF-cap feasibility probe - hfcap.txt (no code change)\n"
    + "=" * 70 + "\n" + report)