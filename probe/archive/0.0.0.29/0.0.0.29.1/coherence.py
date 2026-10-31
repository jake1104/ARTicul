# Coherence gap probe for task 0.0.0.29.1 (read-only on engine; numpy analysis only).
# Per adjacent segment pair on the three demos, using the 0.0.0.24.1 boundary
# table for positions (plan.txt read, sample-exact: predicted lengths must
# equal the re-rendered wav lengths):
#   (a) F1/F2/F3 jump Hz -- Hann-DFT peak-picking in the segment interior
#       (10 ms edges excluded, which also clears the 8 ms blend zones);
#   (b) RMS step dB between segment interiors;
#   (c) centroid trajectory: per-20 ms series, max adjacent-window jump
#       (global per demo + local max around each boundary).
# Fricative-involved boundaries and nuclear-accented segments are derived
# from the plan (phoneme identity + stress) for the 0.0.0.29.2 exclusion lists.

import math
import re
import struct
import wave

import numpy as np

SR = 22050
EDGE = int(0.010 * SR)      # 10 ms interior trim each edge (220 samples)
FWIN = int(0.020 * SR)      # 20 ms analysis window (441 samples)
HOP = FWIN // 2             # 10 ms hop
NFFT = 2048
PLAN = "probe/archive/0.0.0.24/0.0.0.24.1/plan.txt"
FILES = {
    "hello": "probe/0.0.0.29.1/hello.wav",
    "annyeong": "probe/0.0.0.29.1/annyeong.wav",
    "yeobo": "probe/0.0.0.29.1/yeobo.wav",
}
LABELS = {
    "hello": ["h", "E", "l", "o", "U"],
    "annyeong": ["a", "n", "n", "j", "V", "N", "h", "a", "s", "e", "j", "o"],
    "yeobo": ["j", "V", "b", "o", "s", "e", "j", "o"],
}
FRIC = {"s", "h"}  # segments whose excitation/filter path is frication noise


def load_wav(path):
    with wave.open(path, "rb") as w:
        n = w.getnframes()
        raw = w.readframes(n)
    x = np.array(struct.unpack("<%dh" % n, raw), dtype=np.float64) / 32767.0
    return x


def parse_plan(path):
    demos = {}
    cur = None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            m = re.match(r"== (\w+) ::", line)
            if m:
                cur = m.group(1)
                demos[cur] = {"units": [], "bounds": [], "outlen": 0,
                              "lens": [], "fades": [], "work": []}
                continue
            m = re.match(r"u(\d+) sym=(\S+) dur=\d+ms f0=\S+ stress=(\S+) "
                         r"word_final=\S+ pause=\S+ spec=(\S+) seglen=(\d+) "
                         r"gain=([0-9.\-]+)dB", line)
            if m and cur is not None:
                demos[cur]["units"].append({
                    "sym": m.group(2), "stress": m.group(3),
                    "spec": m.group(4), "seglen": int(m.group(5)),
                    "gain": float(m.group(6))})
                continue
            m = re.match(r"work_units=(.*) lens=\[(.*)\] fades=\[(.*)\] "
                         r"predicted_out_len=(\d+)", line)
            if m and cur is not None:
                demos[cur]["work"] = [g.strip("[]").split(",")
                                      for g in m.group(1).split("] [")]
                demos[cur]["work"] = [[int(v) for v in g if v.strip() != ""]
                                      for g in demos[cur]["work"]]
                demos[cur]["lens"] = [int(v) for v in m.group(2).split(",")]
                demos[cur]["fades"] = [int(v) for v in m.group(3).split(",")]
                demos[cur]["outlen"] = int(m.group(4))
                continue
            m = re.match(
                r"b(\d+) between u(\d+)\(.*\)->u(\d+)\(.*\) type=(\S+) "
                r"zone=\[(\d+), (\d+)\) n=(\d+) gain_step=([0-9.]+)dB "
                r"f0_step=([0-9.\-]+)st", line)
            if m and cur is not None:
                demos[cur]["bounds"].append({
                    "b": int(m.group(1)), "prev": int(m.group(2)),
                    "nxt": int(m.group(3)), "type": m.group(4),
                    "z0": int(m.group(5)), "z1": int(m.group(6))})
    return demos


def out_spans(d):
    # Output sample span of each work unit (segment) from concat arithmetic.
    starts, acc = [], 0
    for k, ln in enumerate(d["lens"]):
        starts.append(acc)
        if k + 1 < len(d["lens"]):
            acc += ln - d["fades"][k + 1]
        else:
            acc += ln
    assert acc == d["outlen"], (acc, d["outlen"])
    return list(zip(starts, [s + ln for s, ln in zip(starts, d["lens"])]))


def avg_power(interior):
    # Average power spectrum over 20 ms Hann frames, 10 ms hop.
    win = np.hanning(FWIN)
    specs = []
    p = 0
    while p + FWIN <= len(interior):
        fr = interior[p:p + FWIN] * win
        specs.append(np.abs(np.fft.rfft(fr, NFFT)) ** 2)
        p += HOP
    if not specs:  # shortest interior still fits several frames; fallback
        fr = interior * np.hanning(len(interior))
        specs.append(np.abs(np.fft.rfft(fr, NFFT)) ** 2)
    return np.mean(np.stack(specs), axis=0)


def pick_peak(power, flo, fhi, fmin=None):
    freqs = np.fft.rfftfreq(NFFT, 1.0 / SR)
    lo = int(np.searchsorted(freqs, flo))
    hi = int(np.searchsorted(freqs, fhi))
    band = power[lo:hi]
    idx = int(np.argmax(band)) + lo
    if fmin is not None:
        # enforce formant ordering: search above fmin
        lo2 = max(idx, int(np.searchsorted(freqs, fmin)))
        if lo2 < hi:
            idx = int(np.argmax(power[lo2:hi])) + lo2
    # parabolic interpolation around the peak bin
    if 0 < idx < len(power) - 1:
        a, b, c = power[idx - 1], power[idx], power[idx + 1]
        d = (a - c) / (2.0 * (a - 2.0 * b + c)) if (a - 2 * b + c) != 0 else 0.0
        d = max(-0.5, min(0.5, d))
        return (idx + d) * SR / NFFT
    return idx * SR / NFFT


def formants(interior):
    p = avg_power(interior)
    f1 = pick_peak(p, 200, 1000)
    f2 = pick_peak(p, 800, 2800, fmin=f1 + 50)
    f3 = pick_peak(p, 1800, 4200, fmin=f2 + 100)
    return f1, f2, f3


def rms_db(x):
    return 10.0 * math.log10(max(np.mean(x ** 2), 1e-12))


def centroid_series(x):
    win = np.hanning(FWIN)
    freqs = np.fft.rfftfreq(NFFT, 1.0 / SR)
    cents, centers = [], []
    p = 0
    while p + FWIN <= len(x):
        pw = np.abs(np.fft.rfft(x[p:p + FWIN] * win, NFFT)) ** 2
        tot = pw.sum()
        cents.append(float((freqs * pw).sum() / tot) if tot > 0 else 0.0)
        centers.append(p + FWIN // 2)
        p += HOP
    return np.array(centers), np.array(cents)


def frame_f2(x, p):
    # F2 of a single 20 ms Hann window at offset p (transition-local formant).
    fr = x[p:p + FWIN] * np.hanning(FWIN)
    pw = np.abs(np.fft.rfft(fr, NFFT)) ** 2
    f1 = pick_peak(pw, 200, 1000)
    return pick_peak(pw, 800, 2800, fmin=f1 + 50)


def main():
    demos = parse_plan(PLAN)
    out_lines = []
    gate_f2_viol, gate_rms_viol = [], []
    for label in ["hello", "annyeong", "yeobo"]:
        d = demos[label]
        x = load_wav(FILES[label])
        assert len(x) == d["outlen"], (label, len(x), d["outlen"])
        out_lines.append("== %s wavlen=%d (plan predicted %d: EXACT)" %
                         (label, len(x), d["outlen"]))
        spans = out_spans(d)
        # per-segment interiors + formants + rms
        seginfo = []
        for k, (s0, s1) in enumerate(spans):
            interior = x[s0 + EDGE:s1 - EDGE]
            assert len(interior) > FWIN, (label, k, len(interior))
            f1, f2, f3 = formants(interior)
            seginfo.append({"f": (f1, f2, f3), "rms": rms_db(interior),
                            "span": (s0, s1), "n": len(interior)})
            members = d["work"][k]
            syms = "+".join(LABELS[label][u] for u in members)
            stress = "+".join(d["units"][u]["stress"] for u in members)
            spec = "+".join(d["units"][u]["spec"] for u in members)
            fric = any(LABELS[label][u] in FRIC for u in members)
            out_lines.append(
                "   seg work[%s]=%s stress=%s spec=%s span=[%d,%d) "
                "interior_n=%d F1=%.0f F2=%.0f F3=%.0f rms=%.2fdBFS%s" %
                (k, syms, stress, spec, s0, s1, len(interior),
                 f1, f2, f3, seginfo[-1]["rms"],
                 " FRICATIVE" if fric else ""))
        # per-boundary jumps
        centers, cents = centroid_series(x)
        jumps = np.abs(np.diff(cents))
        gmax = float(jumps.max())
        out_lines.append("   centroid series: %d frames(20ms/10ms-hop) "
                         "global max adjacent jump=%.0fHz" % (len(cents), gmax))
        out_lines.append("   -- boundaries (interior-to-interior) --")
        for b in d["bounds"]:
            k = {"hello": {1: 0, 2: 1, 3: 2},
                 "annyeong": {n: n - 1 for n in range(1, 12)},
                 "yeobo": {n: n - 1 for n in range(1, 8)}}[label][b["b"]]
            f0, f1v = seginfo[k]["f"], seginfo[k + 1]["f"]
            d1, d2, d3 = (abs(f1v[0] - f0[0]), abs(f1v[1] - f0[1]),
                          abs(f1v[2] - f0[2]))
            rstep = seginfo[k + 1]["rms"] - seginfo[k]["rms"]
            pl = "+".join(LABELS[label][u] for u in d["work"][k])
            nl = "+".join(LABELS[label][u] for u in d["work"][k + 1])
            fric = (any(LABELS[label][u] in FRIC for u in d["work"][k]) or
                    any(LABELS[label][u] in FRIC for u in d["work"][k + 1]))
            zc = (b["z0"] + b["z1"]) // 2
            local = jumps[np.array(
                [abs(c - zc) < int(0.030 * SR) for c in centers[:-1]])]
            lmax = float(local.max()) if len(local) else 0.0
            tag = " FRIC" if fric else ""
            out_lines.append(
                "   b%d %s->%s pos=%.1fms |dF1|=%.0fHz |dF2|=%.0fHz "
                "|dF3|=%.0fHz RMSstep=%+.2fdB centroid-localmax=%.0fHz "
                "globalmax=%.0fHz%s" %
                (b["b"], pl, nl, b["z0"] / SR * 1000.0,
                 d1, d2, d3, rstep, lmax, gmax, tag))
            if not fric:
                if d2 > 150:
                    gate_f2_viol.append((label, b["b"], d2))
                if abs(rstep) > 4:
                    gate_rms_viol.append((label, b["b"], rstep))
    out_lines.append("GATE-CHECK non-fricative boundaries: F2>150Hz count=%d %s" %
                     (len(gate_f2_viol), gate_f2_viol))
    out_lines.append("GATE-CHECK non-fricative boundaries: |RMSstep|>4dB count=%d %s" %
                     (len(gate_rms_viol), gate_rms_viol))
    worst_f2 = max(gate_f2_viol, key=lambda t: t[2]) if gate_f2_viol else None
    worst_r = (max(gate_rms_viol, key=lambda t: abs(t[2]))
               if gate_rms_viol else None)
    out_lines.append("WORST non-fricative |dF2|=%s WORST |RMSstep|=%s" %
                     (worst_f2, worst_r))
    # Table C: transition-local F2 (nose-to-nose 20 ms windows flanking the
    # blend zone, 0.0.0.24.1 convention) + corridor slope (max adjacent-frame
    # |dF2| with frame centers inside +/-25 ms of boundary center).
    out_lines.append("== transition-local F2 (per-frame 20ms Hann / 10ms hop)")
    for label in ["hello", "annyeong", "yeobo"]:
        d = demos[label]
        x = load_wav(FILES[label])
        out_lines.append("== %s" % label)
        for b in d["bounds"]:
            z0, z1, zc = b["z0"], b["z1"], (b["z0"] + b["z1"]) // 2
            # last fully-pre-zone frame, first fully-post-zone frame
            p_pre = max(0, z0 - FWIN)
            while p_pre + FWIN > z0:
                p_pre -= 1
            p_post = z1
            f2pre, f2post = frame_f2(x, p_pre), frame_f2(x, p_post)
            # corridor slope: frames with centers within 25 ms of zc
            f2traj, cc = [], []
            p = max(0, zc - int(0.040 * SR))
            while p + FWIN <= min(len(x), zc + int(0.040 * SR)):
                f2traj.append(frame_f2(x, p))
                cc.append(p + FWIN // 2)
                p += HOP
            slopes = [abs(f2traj[i + 1] - f2traj[i]) for i in range(len(f2traj) - 1)
                      if abs(cc[i] - zc) < int(0.025 * SR) or
                      abs(cc[i + 1] - zc) < int(0.025 * SR)]
            k = {"hello": {1: 0, 2: 1, 3: 2},
                 "annyeong": {n: n - 1 for n in range(1, 12)},
                 "yeobo": {n: n - 1 for n in range(1, 8)}}[label][b["b"]]
            pl = "+".join(LABELS[label][u] for u in d["work"][k])
            nl = "+".join(LABELS[label][u] for u in d["work"][k + 1])
            fric = (any(LABELS[label][u] in FRIC for u in d["work"][k]) or
                    any(LABELS[label][u] in FRIC for u in d["work"][k + 1]))
            out_lines.append(
                "   b%d %s->%s noseF2 pre=%.0f post=%.0f |d|=%.0fHz "
                "corridor-max-per-frame=%.0fHz%s" %
                (b["b"], pl, nl, f2pre, f2post, abs(f2post - f2pre),
                 max(slopes) if slopes else 0.0,
                 " FRIC" if fric else ""))
    text = "\n".join(out_lines) + "\n"
    print(text)
    with open("probe/0.0.0.29.1/coherence.txt", "w", encoding="utf-8") as f:
        f.write(text)


main()
