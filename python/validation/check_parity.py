import sys

import numpy as np
from scipy.signal import welch

from articul import lookup, synthesize


def main():
    p = lookup("p")
    assert p is not None, "lookup p"
    assert p["place"] == "Bilabial", p
    assert p["manner"] == "Plosive", p
    assert p["voiced"] is False, p
    print("PASS lookup-p")

    assert lookup("?") is None
    print("PASS lookup-unknown")

    x = synthesize("hi")
    assert isinstance(x, np.ndarray), type(x)
    assert x.size > 0, "empty render"
    assert np.all(np.isfinite(x)), "non-finite sample"
    assert np.max(np.abs(x)) > 0.01, "silent render"
    print(f"PASS synthesize len={x.size}")

    v = synthesize("a").astype(float)
    freqs, psd = welch(v, fs=22050, nperseg=min(4096, v.size))
    f1 = np.sum(psd[(freqs >= 500) & (freqs <= 900)])
    f2 = np.sum(psd[(freqs >= 900) & (freqs <= 1400)])
    ratio = float(f2 / max(f1, 1e-12))
    assert 0.05 <= ratio <= 0.5, f"f2/f1={ratio}"
    print(f"PASS vowel-a f2/f1={ratio:.3f}")


if __name__ == "__main__":
    sys.exit(main())
