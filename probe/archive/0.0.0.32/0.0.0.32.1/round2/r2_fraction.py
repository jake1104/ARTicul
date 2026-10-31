 # FRACTION-cap feasibility simulation for task 0.0.0.32.1 round-2 (read-only, no engine change).
# Per-segment HF-FRACTION limiter: for each NON-FRICATIVE voiced segment, scale
# its 4kHz+ band amplitude by g so its post HF-fraction f' <= K * utterance-median
# voiced HF-fraction. Closed form: g^2 = cap*(1-f)/(f*(1-cap)), f = E_hf/E_tot on
# the whole-interior FFT; g = 1 where f <= cap. Fricatives (/s/, /h/) and the /b/
# burst are untouched (gain 1). Band split is a whole-utterance FFT brickwall
# (ideal); per-sample gain track with raised-cosine smoothing across engine blend
# zones (176 samples) and the GOAT internal edge (110 samples).
# Metrics per K in {1.5, 2.0, 3.0}:
#  (a) voiced HF-fraction max/min ratio (whole-interior FFT, texture.py method)
#  (b) sibilant HF preservation (dB change on /s/ interiors)
#  (c) lateral notch depth on hello 170-210ms window (0.0.0.20.2 metric)
#  (d) per-demo broadband RMS delta vs baseline
#  (e) NEW: HF-band scaling factors per segment (min/med/max); flag cuts < -6dB

import re
import math
import struct
import wave
import numpy as np

SR = 22050
EDGE = int(0.010 * SR)
CUTOFF = 4000.0
KS = [1.5, 2.0, 3.0]
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
    # FRACTION-targeted cap: per-segment whole-interior HF-fraction f_i,
    # cap = K * median(f); g_i^2 = cap*(1-f_i)/(f_i*(1-cap)) where f_i > cap.
    _, hf = split_hp(x, cutoff)
    fr0 = {}
    for i in vset:
        s, e = ranges[i]
        seg = x[s + EDGE:e - EDGE]
        n = len(seg)
        X = np.fft.rfft(seg)
        freqs = np.fft.rfftfreq(n, 1.0 / SR)
        P = X.real ** 2 + X.imag ** 2
        tot = P.sum()
        fr0[i] = float(P[freqs >= cutoff].sum() / tot) if tot > 0 else 0.0
    med = float(np.median([fr0[i] for i in vset]))
    cap = K * med
    gains = np.ones(nunits)
    for i in vset:
        f = fr0[i]
        if f > cap and 0.0 < cap < 1.0:
            g2 = cap * (1.0 - f) / (f * (1.0 - cap))
            gains[i] = min(1.0, float(math.sqrt(max(g2, 0.0))))
    track = build_track(len(x), ranges, nunits, gains, zones, goat_splits)
    lf = x - hf
    y = lf + track * hf
    return y, gains, med, fr0


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
        # (e) HF-band scaling factors on the vset + by-construction check
        gv = np.array([gains[i] for i in d["vset"]])
        gdb = 20 * np.log10(np.maximum(gv, 1e-12))
        deep = [(i, LABELS[name][i], CLASS[name][i], float(gdb[k]))
                for k, i in enumerate(d["vset"]) if gdb[k] < -6.0]
        r["deep"] = deep
        r["gdb_min"] = float(gdb.min())
        s = ("  band scaling (vset HF gain): min=%.3f (%+.2fdB) med=%.3f (%+.2fdB) max=%.3f (%+.2fdB)"
             % (float(gv.min()), float(gdb.min()), float(np.median(gv)),
                float(np.median(gdb)), float(gv.max()), float(gdb.max())))
        if deep:
            s += " DEEP-CUTS@" + ",".join(
                "u%d(%s/%s%s,%.1fdB)" % (i, sym, cl, "[CORE-VOWEL]" if cl == "V" else "", db)
                for i, sym, cl, db in deep)
        else:
            s += " no-cut-deeper-than-6dB"
        out_lines.append(s)
        cap = K * med
        over = max([fr[i] / cap for i in capped]) if capped and cap > 0 else 0.0
        out_lines.append("  construction check: cap=%.6f max(post-frac/cap) over capped segs=%.4f %s"
                         % (cap, over, "OK(<=1+tol)" if over <= 1.01 else "VIOLATED"))
        if name == "hello":
            out_lines.append("  notch: base=%.2f sim=%.2f delta=%+.4f dB"
                             % (base[name]["notch"], r["notch"], r["notch_delta"]))
        out_lines.append("  fricative HF preservation dB: "
                         + " ".join("%s=%+.4f" % kv for kv in sorted(r["pres"].items())))
# band-edge sensitivity (adversarial variant): rerun full sim at 3.5k with matching
# metric cutoff, watch (a) ratio movement (whole-interior method throughout).
# Question: does the round-2 verdict still hold off the 4.0k design point?
sens = {}
cut = 3500.0
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
        sens[(K, name)] = float(fr.max() / fr.min())
sens_max = 0.0
for K in KS:
    for name in data:
        sens_max = max(sens_max, abs(sens[(K, name)] - results[K][name]["ratio"]))
out_lines.append("band-edge sensitivity (3.5k, whole-interior): max |dratio| = %.4f" % sens_max)
out_lines.append("sensitivity table (a) ratio at 3.5k vs 4.0k:")
for K in KS:
    row = []
    for name in data:
        row.append("%s:%.2f/%.2f" % (name, sens[(K, name)], results[K][name]["ratio"]))
    out_lines.append("  K=%.1f %s" % (K, " ".join(row)))
out_lines.append("sensitivity verdict check (a) at 3.5k with same 2u margin:")
for K in KS:
    cells = []
    for name in data:
        ok = (sens[(K, name)] + 2 * 0.1) <= 3.0
        cells.append("%s:%s" % (name, "PASS" if ok else "FAIL"))
    out_lines.append("  K=%.1f (a@3.5k) %s" % (K, ",".join(cells)))
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
# verdict with 2x margins + (e) audibility gate (no segment cut deeper than -6dB)
A_T, B_T, C_T, D_T = 3.0, 0.5, 6.0, 1.0
U_B, U_C = 0.01, 0.05
u_ratio = U_A
out_lines.append("--- verdict (2x-margin acceptance) ---")
out_lines.append("bounds: u_ratio=%.1f u_b=%.2f u_c=%.2f u_d=%.3f" % (u_ratio, U_B, U_C, u_d))
out_lines.append("accept: (a) sim+2u<=%.1f | (b) |sim|+2u<=%.1f | (c) sim-2u>=%.1f | (d) |sim|+2u<=%.1f | (e) no vset cut < -6dB"
                 % (A_T, B_T, C_T, D_T))
binding = []
passing = []
for K in KS:
    cells = []
    for name in data:
        r = results[K][name]
        a_ok = (r["ratio"] + 2 * u_ratio) <= A_T
        d_ok = (abs(r["rms_db"]) + 2 * u_d) <= D_T
        e_ok = len(r["deep"]) == 0
        cells.append((name, a_ok, d_ok, e_ok))
        if not a_ok:
            binding.append("K=%.1f %s (a) ratio %.2f + 2u(%.1f) = %.2f > 3.0"
                           % (K, name, r["ratio"], u_ratio, r["ratio"] + 2 * u_ratio))
        if not d_ok:
            binding.append("K=%.1f %s (d) |rms| %.4f + 2u(%.3f) > 1.0" % (K, name, abs(r["rms_db"]), u_d))
        if not e_ok:
            binding.append("K=%.1f %s (e) deep HF-band cut(s) %s (min gain %+.2fdB < -6dB)" %
                           (K, name,
                            ",".join("u%d(%s/%s)" % (i, sym, cl) for i, sym, cl, _ in r["deep"]),
                            r["gdb_min"]))
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
    allok = all(a and d and e for _, a, d, e in cells) and b_ok and c_ok
    if allok:
        passing.append(K)
    out_lines.append("K=%.1f: (a) %s (b) %s (c) %s (d) %s (e) %s => %s"
                     % (K, ",".join("%s:%s" % (n, "PASS" if a else "FAIL") for n, a, _, _ in cells),
                        "PASS" if b_ok else "FAIL", "PASS" if c_ok else "FAIL",
                        ",".join("%s:%s" % (n, "PASS" if dd else "FAIL") for n, _, dd, _ in cells),
                        ",".join("%s:%s" % (n, "PASS" if ee else "FAIL") for n, _, _, ee in cells),
                        "PASS" if allok else "FAIL"))
if passing:
    out_lines.append("VERDICT: PASS at K=%s" % passing)
    for K in passing:
        deepv = [(n, i, sym) for n in data for (i, sym, cl, _) in results[K][n]["deep"] if cl == "V"]
        if deepv:
            out_lines.append("  WARNING K=%.1f: passing K needs >-6dB cuts on CORE VOWELS %s" % (K, deepv))
        else:
            out_lines.append("  K=%.1f: no deep cuts on core vowels" % K)
else:
    out_lines.append("VERDICT: NO-PASSING-POINT (%d binding cells):" % len(binding))
    out_lines.extend("  BINDING: " + b for b in binding)
report = "\n".join(out_lines) + "\n"
print(report, end="")
open(ROOT + r"\probe\0.0.0.32.1\round2\r2_fraction.txt", "w", encoding="utf-8").write(
    "0.0.0.32.1 round-2 FRACTION-cap feasibility probe - r2_fraction.txt (no code change)\n"
    + "=" * 70 + "\n" + report)