"""0.0.0.25.1 sensitivity sweep: crest stats + per-boundary crest values."""
import wave
import numpy as np
import sys
sys.path.insert(0, "probe/0.0.0.25.1")
from sparks import load_wav, crest_track, BOUNDARIES, SR, HOP

for name, path in [("hello", "probe/0.0.0.25.1/hello.wav"),
                   ("annyeong", "probe/0.0.0.25.1/annyeong.wav"),
                   ("yeobo", "probe/0.0.0.25.1/yeobo.wav")]:
    x = load_wav(path)
    peak, rms, crest = crest_track(x)
    print("== %s: crest median=%.2f p90=%.2f p99=%.2f max=%.2f at %.1fms" % (
        name, float(np.median(crest)), float(np.percentile(crest, 90)),
        float(np.percentile(crest, 99)), float(crest.max()),
        float(np.argmax(crest)) * HOP / SR * 1000.0))
    # top-12 crest frames
    idx = np.argsort(crest)[::-1][:12]
    print("   top frames (ms, crest, peak):", sorted(
        [(round(float(i) * HOP / SR * 1000.0, 1), round(float(crest[i]), 2),
          round(float(peak[i]), 4)) for i in idx], key=lambda t: t[0]))
    # crest at each boundary (+-10ms max) and local median ratio
    for b in BOUNDARIES[name]:
        c = int(round(b / 1000.0 * SR / HOP))
        lo = max(0, c - 10)
        hi = min(len(crest), c + 11)
        seg = crest[lo:hi]
        k = int(np.argmax(seg)) + lo
        med = float(np.median(crest[max(0, k - 100):k])) if k > 0 else float("nan")
        print("   b=%7.1fms maxcrest=%.2f at %.1fms (ratio %.2f, peak %.4f)" % (
            b, float(seg.max()), k * HOP / SR * 1000.0,
            float(seg.max()) / med if med else 0.0, float(peak[k])))
