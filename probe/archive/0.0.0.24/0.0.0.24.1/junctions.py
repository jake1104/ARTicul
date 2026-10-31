# Junction spectral probe for task 0.0.0.24.1 (read-only, no engine change).
# Parses probe/0.0.0.24.1/plan.txt, loads the re-rendered wavs, and for every
# inter-segment boundary reports MFCC(13, no c0) euclidean distance between
# 20 ms windows on each side of the blend zone (nose-to-nose, zone excluded),
# plus interior-control distances (adjacent 20 ms windows away from zones).
# Uses only the Python standard library.

import re
import math
import wave

SR = 22050
WIN = int(0.020 * SR)  # 441 samples, 20 ms
NFFT = 512
NMEL = 26
NCEPS = 13  # c1..c13, c0 excluded
FMIN = 0.0
FMAX = SR / 2.0

LABELS = {
    "hello": ["h", "E", "l", "o", "U"],
    "annyeong": ["a", "n", "n", "j", "V", "N", "h", "a", "s", "e", "j", "o"],
    "yeobo": ["j", "V", "b", "o", "s", "e", "j", "o"],
}
FILES = {
    "hello": "probe/0.0.0.24.1/hello.wav",
    "annyeong": "probe/0.0.0.24.1/annyeong.wav",
    "yeobo": "probe/0.0.0.24.1/yeobo.wav",
}


def load_wav(path):
    with wave.open(path, "rb") as w:
        n = w.getnframes()
        data = w.readframes(n)
    import struct
    x = struct.unpack("<%dh" % n, data)
    return [v / 32767.0 for v in x]


def hz_to_mel(h):
    return 2595.0 * math.log10(1.0 + h / 700.0)


def mel_to_hz(m):
    return 700.0 * (10.0 ** (m / 2595.0) - 1.0)


def mel_bank():
    mlo = hz_to_mel(FMIN)
    mhi = hz_to_mel(FMAX)
    pts = [mel_to_hz(mlo + (mhi - mlo) * k / (NMEL + 1)) for k in range(NMEL + 2)]
    bins = [p * NFFT / SR for p in pts]
    fb = [[0.0] * (NFFT // 2 + 1) for _ in range(NMEL)]
    for m in range(NMEL):
        lo, c, hi = bins[m], bins[m + 1], bins[m + 2]
        for k in range(NFFT // 2 + 1):
            f = float(k)
            if lo <= f < c and c > lo:
                fb[m][k] = (f - lo) / (c - lo)
            elif c <= f <= hi and hi > c:
                fb[m][k] = (hi - f) / (hi - c)
    return fb


FB = mel_bank()

# Hamming window, precomputed.
HAM = [0.54 - 0.46 * math.cos(2.0 * math.pi * n / (WIN - 1)) for n in range(WIN)]

# DCT-II matrix for c1..c13 over NMEL log energies.
DCT = [
    [
        math.cos(math.pi * (2.0 * n + 1.0) * k / (2.0 * NMEL))
        * (math.sqrt(2.0 / NMEL))
        for n in range(NMEL)
    ]
    for k in range(1, NCEPS + 1)
]


def dft_mag(frame):
    # Naive DFT magnitudes for NFFT=512 real input; frame length WIN, zero-padded.
    mags = []
    for k in range(NFFT // 2 + 1):
        re = 0.0
        im = 0.0
        ang_step = -2.0 * math.pi * k / NFFT
        for n in range(WIN):
            a = ang_step * n
            s = frame[n]
            re += s * math.cos(a)
            im += s * math.sin(a)
        mags.append(math.sqrt(re * re + im * im))
    return mags


def mfcc_no_c0(seg):
    # seg: WIN samples. Returns 13 coeffs (c1..c13).
    emph = [0.0] * WIN
    prev = 0.0
    for n in range(WIN):
        emph[n] = (seg[n] - 0.97 * prev) * HAM[n]
        prev = seg[n]
    mags = dft_mag(emph)
    out = []
    for m in range(NMEL):
        e = 0.0
        row = FB[m]
        for k in range(NFFT // 2 + 1):
            e += mags[k] * row[k]
        out.append(math.log(max(e, 1e-10)))
    return [sum(DCT[k][n] * out[n] for n in range(NMEL)) for k in range(NCEPS)]


def dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def parse_plan(path):
    demos = {}
    cur = None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            m = re.match(r"== (\w+) ::", line)
            if m:
                cur = m.group(1)
                demos[cur] = {"units": [], "bounds": [], "outlen": 0}
                continue
            m = re.match(
                r"b(\d+) between u(\d+)\(.*\)->u(\d+)\(.*\) type=(\S+) zone=\[(\d+), (\d+)\) n=(\d+) gain_step=([0-9.]+)dB f0_step=([0-9.\-]+)st",
                line,
            )
            if m and cur is not None:
                demos[cur]["bounds"].append(
                    {
                        "b": int(m.group(1)),
                        "prev": int(m.group(2)),
                        "nxt": int(m.group(3)),
                        "type": m.group(4),
                        "z0": int(m.group(5)),
                        "z1": int(m.group(6)),
                        "n": int(m.group(7)),
                        "gain": float(m.group(8)),
                        "f0st": float(m.group(9)),
                    }
                )
                continue
            m = re.search(r"predicted_out_len=(\d+)", line)
            if m and cur is not None:
                demos[cur]["outlen"] = int(m.group(1))
    return demos


def rms(seg):
    return math.sqrt(sum(v * v for v in seg) / max(len(seg), 1))


def main():
    demos = parse_plan("probe/0.0.0.24.1/plan.txt")
    for label in ["hello", "annyeong", "yeobo"]:
        d = demos[label]
        x = load_wav(FILES[label])
        assert len(x) == d["outlen"], (label, len(x), d["outlen"])
        print("== %s wavlen=%d" % (label, len(x)))
        ctl = []
        # Interior controls: adjacent 20 ms window pairs on a 40 ms grid,
        # skipping anything within one window of a blend zone.
        zones = [(b["z0"], b["z1"]) for b in d["bounds"]]
        centers = []
        step = 882  # 40 ms grid
        p = WIN
        while p + 2 * WIN < len(x):
            if not any(z0 - WIN < p < z1 + WIN for z0, z1 in zones):
                centers.append(p)
            p += step
        for p in centers[:12]:
            ctl.append(dist(mfcc_no_c0(x[p:p + WIN]), mfcc_no_c0(x[p + WIN:p + 2 * WIN])))
        ctl_sorted = sorted(ctl)
        med = ctl_sorted[len(ctl_sorted) // 2] if ctl_sorted else float("nan")
        print("   interior-control n=%d median=%.3f max=%.3f" % (len(ctl), med, max(ctl) if ctl else float("nan")))
        for b in d["bounds"]:
            z0, z1 = b["z0"], b["z1"]
            pre0 = max(z0 - WIN, 0)
            post1 = min(z1 + WIN, len(x))
            assert z0 - pre0 == WIN, (label, b["b"], "pre clamp")
            assert post1 - z1 == WIN, (label, b["b"], "post clamp")
            mj = dist(mfcc_no_c0(x[pre0:z0]), mfcc_no_c0(x[z1:post1]))
            rl = 20.0 * math.log10(rms(x[z1:post1]) / max(rms(x[pre0:z0]), 1e-9))
            pl = LABELS[label][b["prev"]]
            nl = LABELS[label][b["nxt"]]
            print(
                "   b%d %s->%s pos=%.1fms type=%s gain=%.1fdB realised=%+.1fdB f0=%+.3fst mfcc=%.3f"
                % (
                    b["b"],
                    pl,
                    nl,
                    z0 / SR * 1000.0,
                    b["type"],
                    b["gain"],
                    rl,
                    b["f0st"],
                    mj,
                )
            )
    type_counts = {}
    cas_mfcc = []
    mix_mfcc = []
    for label in ["hello", "annyeong", "yeobo"]:
        d = demos[label]
        x = load_wav(FILES[label])
        for b in d["bounds"]:
            t = b["type"]
            type_counts[t] = type_counts.get(t, 0) + 1
            z0, z1 = b["z0"], b["z1"]
            mj = dist(mfcc_no_c0(x[z0 - WIN:z0]), mfcc_no_c0(x[z1:z1 + WIN]))
            if t == "CASCADE-SHORT-GLIDE":
                cas_mfcc.append(mj)
            elif t == "MIXED-LINEAR":
                mix_mfcc.append(mj)
    print("SUMMARY total=%d %s"
          % (sum(type_counts.values()),
             " ".join("%s=%d" % kv for kv in sorted(type_counts.items()))))
    print("SUMMARY cascade-short n=%d mean_mfcc=%.3f"
          % (len(cas_mfcc), sum(cas_mfcc) / max(len(cas_mfcc), 1)))
    print("SUMMARY mixed-linear n=%d mean_mfcc=%.3f"
          % (len(mix_mfcc), sum(mix_mfcc) / max(len(mix_mfcc), 1)))


main()
