# Center-third nucleus check for task 0.0.0.33.1 (midpoint F2 free of
# edge transitions) + locus-pull arithmetic cross-check.
import struct
import wave

import numpy as np

import sys
sys.path.insert(0, "probe/0.0.0.33.1")
from measure import load_wav, avg_power, pick_peak, formants, rms_db  # noqa

SR = 22050
EDGE = int(0.010 * SR)
UNITS = [
    ("annyeong", "a-u0", 0, 3947),
    ("annyeong", "V-u4", 6286, 8226),
    ("annyeong", "a-u7", 9837, 12439),
    ("annyeong", "o-u11", 15373, 17446),
    ("yeobo", "V-u1", 772, 3639),
    ("yeobo", "o-u3", 4191, 6462),
    ("yeobo", "o-u7", 10807, 14666),
    ("hello", "E-u1", 1544, 3506),
]


def main():
    wavs = {
        "hello": load_wav("probe/0.0.0.33.1/hello.wav"),
        "annyeong": load_wav("probe/0.0.0.33.1/annyeong.wav"),
        "yeobo": load_wav("probe/0.0.0.33.1/yeobo.wav"),
    }
    lines = []
    for label, uname, s0, s1 in UNITS:
        x = wavs[label]
        inter = x[s0 + EDGE:s1 - EDGE]
        q = len(inter) // 3
        f_full = formants(inter)
        f_mid = formants(inter[q:2 * q]) if q > 200 else f_full
        lines.append("%s %s full F1=%.0f F2=%.0f F3=%.0f | mid-third "
                     "F1=%.0f F2=%.0f F3=%.0f" % ((label, uname) + f_full +
                                                  f_mid))
    text = "\n".join(lines) + "\n"
    with open("probe/0.0.0.33.1/mid.txt", "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    print("wrote probe/0.0.0.33.1/mid.txt")


if __name__ == "__main__":
    main()
