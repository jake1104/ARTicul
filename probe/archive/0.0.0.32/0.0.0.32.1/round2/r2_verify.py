# Independent adversarial check for round-2 FRACTION-cap result (read-only).
# Hypothesis: the whole-interior FFT HF-fraction is dominated by LF spectral
# leakage through the short interior window, so scaling the 4kHz+ band by g
# cannot move the metric to cap. Test: the LF-only signal (whole-utterance
# brickwall lowpass, untouched by the gain track) already carries an interior
# HF-fraction ("floor") near the POST-sim value. If post ~= floor >> cap,
# the limiter is pushing against leakage, not real HF energy -> (a) can never
# pass no matter how deep the cut (short of muting the band entirely).
import sys
sys.path.insert(0, r"E:\01_coding\ARTicul\probe\0.0.0.32.1\round2")
import numpy as np
from r2_fraction import (data, results, split_hp, hf_frac_interior, EDGE, CUTOFF)

print("== leakage-floor check (K=1.5, 4kHz band edge) ==")
for name in ["hello", "annyeong", "yeobo"]:
    d = data[name]
    x = d["x"]
    lf, _ = split_hp(x, CUTOFF)  # LF part is track-invariant (gain applies to HF only)
    r = results[1.5][name]
    cap = 1.5 * r["med"]
    print("-- %s cap=%.6f" % (name, cap))
    for i in d["vset"]:
        s, e = d["ranges"][i]
        f_base, _, _ = hf_frac_interior(x, s + EDGE, e - EDGE)
        f_post, _, _ = hf_frac_interior(r["y"], s + EDGE, e - EDGE)
        f_floor, _, _ = hf_frac_interior(lf, s + EDGE, e - EDGE)
        g = r["gains"][i]
        print("  u%d base=%.6f post=%.6f post/cap=%.3f floor(LF-only)=%.6f floor/cap=%.3f g=%.3f"
              % (i, f_base, f_post, f_post / cap, f_floor, f_floor / cap, g))
print("== floor-proximity summary ==")
print("if post ~= floor on capped segs, the metric is leakage-bound: deeper cuts")
print("cannot reach cap, so (a) max/min ratio cannot be compressed by this limiter.")
