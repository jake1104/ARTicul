"""0.0.0.25.1 threshold sweep: same detector at 2.0x/2.5x/3.0x + segment context."""
import wave
import numpy as np
import sys
sys.path.insert(0, "probe/0.0.0.25.1")
from sparks import load_wav, crest_track, dominant_band, BOUNDARIES, SR, HOP

# segment spans in output samples (from plan.txt work_units lens/fades):
# out_start(seg k+1) = out_start(seg k) + lens[k] - fades[k+1]
SEGS = {
    "hello": ([1720, 1962, 1544, 5094], [0, 176, 176, 176],
              ["h", "E", "l", "o+U"]),
    "annyeong": ([3947, 1147, 992, 904, 1940, 992, 1147, 2602, 1279, 1455, 904, 2073],
                 [0, 176, 176, 176, 176, 176, 176, 176, 176, 176, 176, 176],
                 ["a", "n", "n", "j", "V", "N", "h", "a", "s", "e", "j", "o"]),
    "yeobo": ([948, 2867, 904, 2271, 1301, 2844, 904, 3859],
              [0, 176, 176, 176, 176, 176, 176, 176],
              ["j", "V", "b", "o", "s", "e", "j", "o"]),
}


def seg_spans(name):
    lens, fades, labels = SEGS[name]
    spans = []
    start = 0
    for k, (L, lab) in enumerate(zip(lens, labels)):
        spans.append((start, start + L, lab))
        if k + 1 < len(lens):
            start = start + L - fades[k + 1]
    return spans


def detect_at(x, thresh):
    peak, rms, crest = crest_track(x)
    nfr = len(crest)
    flag = np.zeros(nfr, dtype=bool)
    for i in range(nfr):
        lo = max(0, i - 100)
        med = float(np.median(crest[lo:i])) if i > lo else float(crest[i])
        med = max(med, 1e-9)
        if peak[i] >= 0.01 and crest[i] > thresh * med:
            flag[i] = True
    out = []
    i = 0
    while i < nfr:
        if not flag[i]:
            i += 1
            continue
        j = i
        while j + 1 < nfr and flag[j + 1]:
            j += 1
        s0 = i * HOP
        s1 = min(len(x), j * HOP + HOP)
        seg = np.abs(x[s0:s1])
        k = int(np.argmax(seg))
        out.append((s0 / SR * 1000.0, (s0 + k) / SR * 1000.0,
                    float(seg[k]), float((j - i + 1) * HOP) / SR * 1000.0,
                    s0 + k))
        i = j + 1
    return out


for thresh in (2.0, 2.5, 3.0, 4.0):
    print("=== threshold %.1fx ===" % thresh)
    gt_tot = gt_hit = 0
    for name, path in [("hello", "probe/0.0.0.25.1/hello.wav"),
                       ("annyeong", "probe/0.0.0.25.1/annyeong.wav"),
                       ("yeobo", "probe/0.0.0.25.1/yeobo.wav")]:
        x = load_wav(path)
        spans = seg_spans(name)
        sparks = detect_at(x, thresh)

        def seg_of(ms):
            s = int(ms / 1000.0 * SR)
            for a, b, lab in spans:
                if a - 176 <= s < b:
                    return lab
            return "?"

        h = m = 0
        for (t0, tp, amp, dur, pp) in sparks:
            d = min(abs(t0 - b) for b in BOUNDARIES[name])
            nb = min(BOUNDARIES[name], key=lambda b: abs(t0 - b))
            band, ratio, share = dominant_band(x, pp)
            tag = "HIT" if d <= 10.0 else "miss"
            if d <= 10.0:
                h += 1
            else:
                m += 1
            print("  %-8s t0=%7.1f peak=%7.1f amp=%.4f dur=%4.1f band=%6s seg=%-4s near=%6.1f d=%5.1f %s" % (
                name, t0, tp, amp, dur, band, seg_of(t0), nb, d, tag))
        print("  %-8s sparks=%d hits=%d miss=%d" % (name, len(sparks), h, m))
        gt_tot += len(sparks)
        gt_hit += h
    print("  TOTAL sparks=%d hits=%d hit_rate=%.2f" % (
        gt_tot, gt_hit, gt_hit / gt_tot if gt_tot else float("nan")))
