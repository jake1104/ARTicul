import wave, struct
import numpy as np
SR = 22050
WIN = int(0.010 * SR)
def load(p):
    w = wave.open(p, "rb")
    n = w.getnframes()
    return np.array(struct.unpack("<%dh" % n, w.readframes(n)), dtype=np.float64) / 32767.0
def lens_ms(kind, ms):
    return max(1, int(round(ms / 1000.0 * SR)))
PLAN = {
    "hello": ([1720, 1962, 1544, 5094], [0, 176, 176, 176], "probe/0.0.0.29.2/hello.wav"),
    "annyeong": ([3947, 1147, 992, 904, 1940, 992, 1147, 2602, 1279, 1455, 904, 2073], [0, 176, 176, 176, 176, 176, 176, 176, 176, 176, 176, 176], "probe/0.0.0.29.2/annyeong.wav"),
    "yeobo": ([948, 2867, 904, 2271, 1301, 2844, 904, 3859], [0, 176, 176, 176, 176, 176, 176, 176], "probe/0.0.0.29.2/yeobo.wav"),
}
for name, (lens, fades, path) in PLAN.items():
    x = load(path)
    starts = []
    acc = 0
    for k, ln in enumerate(lens):
        starts.append(acc)
        acc += ln if k + 1 == len(lens) else ln - fades[k + 1]
    assert acc == len(x), (name, acc, len(x))
    for gi in range(1, len(lens)):
        s = starts[gi]
        seg = x[s:s + WIN]
        a = np.abs(seg)
        uncl = a[a < 0.985]
        peak = float(uncl.max()) if uncl.size else 0.0
        clamped = int((a >= 0.985).sum())
        print("%s start%d pos=%d unclamped=%.4f clamped=%d" % (name, gi, s, peak, clamped))
x = load("probe/0.0.0.29.2/annyeong.wav")
rms = float(np.sqrt(np.mean(x ** 2)))
print("annyeong overall RMS=%.4f" % rms)
