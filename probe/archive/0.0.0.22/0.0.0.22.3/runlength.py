import wave, struct

def load(path):
    with wave.open(path, 'rb') as w:
        n = w.getnframes()
        sr = w.getframerate()
        raw = w.readframes(n)
    px = struct.unpack('<' + 'h' * n, raw)
    return sr, [v / 32768.0 for v in px]

def runs(x, sr, thresh_db):
    w = sr // 50
    nr = []
    for i in range(0, len(x), w):
        seg = x[i:i + w]
        r = (sum(v * v for v in seg) / max(1, len(seg))) ** 0.5
        nr.append(r)
    pk = max(nr)
    res = []
    cur = 0
    for r in nr:
        import math
        edb = 20.0 * math.log10(r / pk) if r > 0 else -99.0
        if edb < thresh_db:
            cur += 1
        else:
            if cur:
                res.append(cur)
            cur = 0
    if cur:
        res.append(cur)
    return pk, [('%.0fms' % (c * 20)) for c in res]

for name in ['hello', 'annyeonghaseyo', 'yeoboseyo']:
    sr, x = load('demo/%s.wav' % name)
    for t in [-25, -27]:
        pk, rr = runs(x, sr, t)
        print('%s thr=%d pk20=%.3f runs=%s' % (name, t, pk, rr))
