"""0.0.0.25.1 final numbers: 2.5x family with band ratio+share; onset check."""
import numpy as np
import sys
sys.path.insert(0, "probe/0.0.0.25.1")
from sparks import load_wav, crest_track, dominant_band, BOUNDARIES, SR, HOP
from sweep2 import detect_at, seg_spans

for name, path in [("hello", "probe/0.0.0.25.1/hello.wav"),
                   ("annyeong", "probe/0.0.0.25.1/annyeong.wav"),
                   ("yeobo", "probe/0.0.0.25.1/yeobo.wav")]:
    x = load_wav(path)
    peak, rms, crest = crest_track(x)
    spans = seg_spans(name)
    print("== %s global peak=%.4f" % (name, float(np.abs(x).max())))
    for (t0, tp, amp, dur, pp) in detect_at(x, 2.5):
        i = int(round(t0 / 1000.0 * SR / HOP))
        med = float(np.median(crest[max(0, i - 100):i])) if i > 0 else float("nan")
        ratio = float(crest[int(round(tp / 1000.0 * SR / HOP))]) / med
        band, bratio, share = dominant_band(x, pp)
        d = min(abs(t0 - b) for b in BOUNDARIES[name])
        nb = min(BOUNDARIES[name], key=lambda b: abs(t0 - b))
        print("  t0=%7.1f peak=%7.1f amp=%.4f dur=%4.1f crest_ratio=%.2f band=%6s band_x=%6.1f share=%.2f near=%6.1f d=%5.1f" % (
            t0, tp, amp, dur, ratio, band, bratio, share, nb, d))
