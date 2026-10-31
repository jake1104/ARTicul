"""0.0.0.34.1 probe: rendered F0 contour (autocorrelation) + vowel formant
spot-checks (averaged-spectrum peak-pick, same convention as 0.0.0.33.1 audit).
Windows: vowel plan-spans mapped proportionally onto the wav (probe approx)."""
import json
import numpy as np

SR = 22050

def load(path):
    raw = open(path, 'rb').read()
    assert raw[:4] == b'RIFF' and raw[8:12] == b'WAVE'
    import struct
    pos, fmt, data = 12, None, None
    while pos < len(raw):
        tag, ln = raw[pos:pos+4], struct.unpack('<I', raw[pos+4:pos+8])[0]
        body = raw[pos+8:pos+8+ln]
        if tag == b'fmt ':
            fmt = struct.unpack('<HHIIHH', body[:16])
        elif tag == b'data':
            data = body
        pos += 8 + ln + (ln & 1)
    assert fmt[0] == 1 and fmt[5] == 16, fmt
    return np.frombuffer(data, dtype=np.int16).astype(np.float64) / 32768.0

def f0_track(x, sr=SR, fmin=60.0, fmax=300.0):
    fw, hop = int(0.020 * sr), int(0.010 * sr)
    win = np.hanning(fw)
    lo, hi = int(sr / fmax), int(sr / fmin)
    out = []
    for st in range(0, len(x) - fw, hop):
        fr = (x[st:st+fw] - x[st:st+fw].mean()) * win
        if np.abs(fr).max() < 1e-4:
            out.append(0.0); continue
        a = np.correlate(fr, fr, 'full')[fw-1:]
        a /= max(a[0], 1e-12)
        seg = a[lo:hi]
        k = int(np.argmax(seg))
        if seg[k] < 0.35:
            out.append(0.0); continue
        lag = float(lo + k)
        if 0 < lo + k < len(a) - 1:
            y0, y1, y2 = a[lo+k-1], a[lo+k], a[lo+k+1]
            d = (y0 - y2) / max(2 * (y0 - 2 * y1 + y2), 1e-12)
            lag += max(-1.0, min(1.0, d))
        out.append(sr / lag)
    return np.array(out)

def formants(x, sr=SR):
    fw, hop = int(0.020 * sr), int(0.010 * sr)
    win = np.hanning(fw)
    acc = None; cnt = 0
    for st in range(0, len(x) - fw, hop):
        fr = (x[st:st+fw] - x[st:st+fw].mean()) * win
        sp = np.abs(np.fft.rfft(fr, n=4096)) ** 2
        acc = sp if acc is None else acc + sp
        cnt += 1
    if cnt == 0:
        return None
    avg = acc / cnt
    freqs = np.fft.rfftfreq(4096, 1.0 / sr)
    mag = 20 * np.log10(avg + 1e-12)
    def peak(flo, fhi, above=None):
        idx = np.where((freqs >= flo) & (freqs <= fhi))[0]
        if above is not None:
            idx = idx[mag[idx] > above]
            if len(idx) == 0:
                return None
        j = idx[int(np.argmax(mag[idx]))]
        if 0 < j < len(mag) - 1:
            y0, y1, y2 = mag[j-1], mag[j], mag[j+1]
            d = (y0 - y2) / max(2 * (y0 - 2 * y1 + y2), 1e-12)
            d = max(-1.0, min(1.0, d))
            f = freqs[j] + d * (freqs[1] - freqs[0])
        else:
            f = freqs[j]
        return (round(float(f), 1), round(float(mag[j]), 1))
    f1 = peak(200, 1000)
    f2 = peak(800, 2800)
    if f2 and f1 and f2[0] < f1[0] + 50:
        f2 = peak(f1[0] + 50, 2800)
    f3 = peak(1800, 4200)
    if f3 and f2 and f3[0] < f2[0] + 100:
        f3 = peak(f2[0] + 100, 4200)
    return (f1, f2, f3)

plan = json.load(open('probe/0.0.0.34.1/plan-values.json'))
for label in ('annyeong', 'yeobo'):
    x = load('probe/0.0.0.34.1/%s.wav' % ('annyeonghaseyo' if label == 'annyeong' else 'yeoboseyo'))
    units = plan[label]
    durs = np.array([u['dur'] for u in units], float)
    bounds = np.concatenate([[0], np.cumsum(durs)])
    scale = len(x) / bounds[-1]
    print('== %s wavlen=%d planms=%.0f' % (label, len(x), bounds[-1]))
    f0 = f0_track(x)
    t = (np.arange(len(f0)) * 0.010 + 0.010)
    sel = t * 1000.0 / 1000.0
    line = []
    for edge in range(0, int(len(x) / SR * 1000), 100):
        fr = f0[(t * 1000 >= edge) & (t * 1000 < edge + 100)]
        fr = fr[fr > 0]
        line.append('%dms:%s' % (edge, round(float(np.median(fr)), 1) if len(fr) else '-'))
    print('F0 per-100ms median: ' + ' '.join(line))
    for i, u in enumerate(units):
        if u['sym'] not in ('a', 'V', 'e', 'o'):
            continue
        a, b = bounds[i] * scale, bounds[i+1] * scale
        mid0 = int(a + (b - a) * 0.30), int(a + (b - a) * 0.70)
        seg = x[mid0[0]:mid0[1]]
        fm = formants(seg)
        s = lambda v: ('%.0fHz/%sdB' % v) if v else '-'
        print('u%d %s stress=%s planf0=%.0f->%.0fHz F1=%s F2=%s F3=%s' % (
            i, u['sym'], u['stress'], u['f0'], u['f0_end'],
            s(fm[0]), s(fm[1]), s(fm[2])))
