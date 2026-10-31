import wave, struct, math

def load(path):
    with wave.open(path, 'rb') as w:
        n = w.getnframes()
        sr = w.getframerate()
        raw = w.readframes(n)
    fmt = '<' + 'h' * n
    px = struct.unpack(fmt, raw)
    return sr, [v / 32768.0 for v in px]

def rms(x):
    return math.sqrt(sum(v * v for v in x) / max(1, len(x)))

def trough_max(x, sr):
    w = sr // 100
    nrms = []
    for i in range(0, len(x), w):
        seg = x[i:i + w]
        nrms.append(rms(seg))
    prev = 10
    worst = 0.0
    for i in range(prev, len(nrms)):
        ctx = sum(nrms[i - prev:i]) / prev
        if ctx <= 1e-9 or nrms[i] <= 1e-9:
            continue
        d = 20.0 * math.log10(nrms[i] / ctx)
        if d < worst:
            worst = d
    return worst, [-20.0 * math.log10(nrms[i] / max(1e-9, sum(nrms[i - prev:i]) / prev)) for i in range(prev, len(nrms))]

for name in ['hello', 'annyeonghaseyo', 'yeoboseyo']:
    sr, x = load('demo/%s.wav' % name)
    peak = max(abs(v) for v in x)
    g = rms(x)
    n3 = len(x) // 3
    tail = rms(x[2 * n3:])
    worst, _ = trough_max(x, sr)
    print('%s sr=%d n=%d peak=%.4f rms=%.4f tail=%.4f trough=%.1fdB' % (name, sr, len(x), peak, g, tail, worst))
