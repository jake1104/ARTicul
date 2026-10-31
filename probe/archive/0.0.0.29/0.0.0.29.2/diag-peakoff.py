import wave, struct
import numpy as np
SR = 22050
WIN = int(0.010 * SR)
CLAMP = 0.985

def load(p):
    w = wave.open(p, "rb")
    n = w.getnframes()
    return np.array(struct.unpack("<%dh" % n, w.readframes(n)), dtype=np.float64) / 32767.0

for name, path, s in (("annyeong-s11", "probe/0.0.0.29.2/declick/annyeong.wav", 15373),
                      ("yeobo-s7", "probe/0.0.0.29.2/declick/yeobo.wav", 10807)):
    x = load(path)
    seg = x[s:s + WIN]
    a = np.abs(seg)
    order = np.argsort(-a)
    print("%s win=[%d,%d) d0val=%.4f" % (name, s, s + WIN, seg[0]))
    for k in order[:5]:
        print("  rank d=%d (%.2fms) val=%.4f %s" % (
            k, k * 1000.0 / SR, a[k], "CLAMPED" if a[k] >= CLAMP else ""))
    print("  clamped-in-window=%d" % int((a >= CLAMP).sum()))
