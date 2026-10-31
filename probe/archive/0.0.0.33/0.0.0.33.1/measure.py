# IPA audit measurements for task 0.0.0.33.1 (read-only on engine; numpy analysis only).
# Method: sample-exact plan spans from probe/archive/0.0.0.24/0.0.0.24.1/plan.txt
# (predicted lengths asserted equal to re-rendered wav lengths), per-nucleus
# interior DFT peak-picking (10 ms edge trim, 20 ms Hann / 10 ms hop averaged
# power spectrum, parabolic interpolation), diphthong early/late split.
import math
import re
import struct
import wave

import numpy as np

SR = 22050
EDGE = int(0.010 * SR)
FWIN = int(0.020 * SR)
HOP = FWIN // 2
NFFT = 2048
PLAN = "probe/archive/0.0.0.24/0.0.0.24.1/plan.txt"
FILES = {
    "hello": "probe/0.0.0.33.1/hello.wav",
    "annyeong": "probe/0.0.0.33.1/annyeong.wav",
    "yeobo": "probe/0.0.0.33.1/yeobo.wav",
}
LABELS = {
    "hello": ["h", "E", "l", "o", "U"],
    "annyeong": ["a", "n", "n", "j", "V", "N", "h", "a", "s", "e", "j", "o"],
    "yeobo": ["j", "V", "b", "o", "s", "e", "j", "o"],
}
# syllable -> list of work-segment indices; nucleus = single work index (or
# (early,late) split for the GOAT glide)
SYLS = {
    "hello": [("he", [0, 1], 1), ("loU", [2, 3], (3, "glide"))],
    "annyeong": [("an", [0, 1], 0), ("nyeong", [2, 3, 4, 5], 4),
                 ("ha", [6, 7], 7), ("se", [8, 9], 9), ("jo", [10, 11], 11)],
    "yeobo": [("yeo", [0, 1], 1), ("bo", [2, 3], 3),
              ("se", [4, 5], 5), ("jo", [6, 7], 7)],
}


def load_wav(path):
    with wave.open(path, "rb") as w:
        n = w.getnframes()
        raw = w.readframes(n)
    return np.array(struct.unpack("<%dh" % n, raw), dtype=np.float64) / 32767.0


def parse_plan(path):
    demos = {}
    cur = None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            m = re.match(r"== (\w+) ::", line)
            if m:
                cur = m.group(1)
                demos[cur] = {"units": [], "lens": [], "fades": [],
                              "outlen": 0, "durs": []}
                continue
            m = re.match(r"u\d+ sym=(\S+) dur=(\d+)ms.*seglen=(\d+) ", line)
            if m and cur is not None:
                demos[cur]["units"].append(m.group(1))
                demos[cur]["durs"].append(int(m.group(2)))
                continue
            m = re.match(r"work_units=(.*) lens=\[(.*)\] fades=\[(.*)\] "
                         r"predicted_out_len=(\d+)", line)
            if m and cur is not None:
                demos[cur]["lens"] = [int(v) for v in m.group(2).split(",")]
                demos[cur]["fades"] = [int(v) for v in m.group(3).split(",")]
                demos[cur]["outlen"] = int(m.group(4))
    return demos


def out_spans(d):
    starts, acc = [], 0
    for k, ln in enumerate(d["lens"]):
        starts.append(acc)
        acc += ln if k + 1 == len(d["lens"]) else ln - d["fades"][k + 1]
    assert acc == d["outlen"], (acc, d["outlen"])
    return list(zip(starts, [s + ln for s, ln in zip(starts, d["lens"])]))


def avg_power(interior):
    win = np.hanning(FWIN)
    specs = []
    p = 0
    while p + FWIN <= len(interior):
        fr = interior[p:p + FWIN] * win
        specs.append(np.abs(np.fft.rfft(fr, NFFT)) ** 2)
        p += HOP
    if not specs:
        fr = interior * np.hanning(len(interior))
        specs.append(np.abs(np.fft.rfft(fr, NFFT)) ** 2)
    return np.mean(np.stack(specs), axis=0)


def pick_peak(power, flo, fhi, fmin=None):
    freqs = np.fft.rfftfreq(NFFT, 1.0 / SR)
    lo = int(np.searchsorted(freqs, flo))
    hi = int(np.searchsorted(freqs, fhi))
    idx = int(np.argmax(power[lo:hi])) + lo
    if fmin is not None:
        lo2 = max(idx, int(np.searchsorted(freqs, fmin)))
        if lo2 < hi:
            idx = int(np.argmax(power[lo2:hi])) + lo2
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


def main():
    demos = parse_plan(PLAN)
    lines = []
    for label in ["hello", "annyeong", "yeobo"]:
        d = demos[label]
        x = load_wav(FILES[label])
        ok = "EXACT" if len(x) == d["outlen"] else "MISMATCH"
        lines.append("== %s wavlen=%d plan=%d %s" % (label, len(x),
                                                     d["outlen"], ok))
        spans = out_spans(d)
        for name, members, nuc in SYLS[label]:
            s0, s1 = spans[members[0]][0], spans[members[-1]][1]
            lines.append(" syllable %-6s span=[%d,%d) = %.1f..%.1fms" %
                         (name, s0, s1, s0 / SR * 1000, s1 / SR * 1000))
            for u in members:
                us0, us1 = spans[u]
                f1, f2, f3 = formants(x[us0 + EDGE:us1 - EDGE])
                lines.append("   unit %-4s sym=%-3s plandur=%dms spans=%.1fms "
                             "F1=%.0f F2=%.0f F3=%.0f rms=%.2fdBFS" %
                             ("u%d" % u, d["units"][u], d["durs"][u],
                              (us1 - us0) / SR * 1000, f1, f2, f3,
                              rms_db(x[us0 + EDGE:us1 - EDGE])))
            if isinstance(nuc, tuple):
                k, _ = nuc
                us0, us1 = spans[k]
                inter = x[us0 + EDGE:us1 - EDGE]
                q = len(inter) // 3
                e = formants(inter[:q]) if q > FWIN else formants(inter)
                lt = formants(inter[-q:]) if q > FWIN else formants(inter)
                lines.append("   glide early F1=%.0f F2=%.0f F3=%.0f | "
                             "late F1=%.0f F2=%.0f F3=%.0f" % (e + lt))
    text = "\n".join(lines) + "\n"
    with open("probe/0.0.0.33.1/measure.txt", "w", encoding="utf-8") as f:
        f.write(text)
    safe = text.encode("ascii", errors="replace").decode("ascii")
    print(safe)
    print("wrote probe/0.0.0.33.1/measure.txt")


if __name__ == "__main__":
    main()
