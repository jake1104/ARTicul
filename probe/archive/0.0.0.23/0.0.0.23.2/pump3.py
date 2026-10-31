import math
import sys


def pump_metric(path):
    gains = []
    with open(path) as f:
        for line in f:
            gains.append(float(line.split()[3].split('=')[1]))
    n = len(gains)
    fs = 50.0
    sx = sum(range(n))
    sxx = sum(i * i for i in range(n))
    sy = sum(gains)
    sxy = sum(i * g for i, g in enumerate(gains))
    slope = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    icept = (sy - slope * sx) / n
    x = [g - (slope * i + icept) for i, g in enumerate(gains)]
    nfft = 1
    while nfft < n:
        nfft *= 2
    xz = x + [0.0] * (nfft - n)
    re = [0.0] * nfft
    im = [0.0] * nfft
    kept = []
    for k in range(nfft):
        s_r = 0.0
        s_i = 0.0
        for t in range(nfft):
            a = 2.0 * math.pi * k * t / nfft
            s_r += xz[t] * math.cos(a)
            s_i -= xz[t] * math.sin(a)
        f = k * fs / nfft
        if 3.0 <= f <= 8.0:
            re[k] = s_r
            im[k] = s_i
            kept.append(k)
        else:
            mirror = (nfft - k) % nfft
            mf = mirror * fs / nfft
            if k != 0 and 3.0 <= mf <= 8.0:
                re[k] = s_r
                im[k] = s_i
                kept.append(k)
    bp = []
    for t in range(n):
        s = 0.0
        for k in range(nfft):
            a = 2.0 * math.pi * k * t / nfft
            s += (re[k] * math.cos(a) - im[k] * math.sin(a)) / nfft
        bp.append(s)
    bs = sorted(bp)
    p5 = bs[int(0.05 * n)]
    p95 = bs[int(0.95 * n)]
    return {
        'windows': n,
        'slope': slope,
        'kept': kept,
        'p95_p5': p95 - p5,
        'peak_to_peak': max(bp) - min(bp),
        'raw_swing': max(gains) - min(gains),
    }


if __name__ == '__main__':
    for path in sys.argv[1:]:
        m = pump_metric(path)
        print('%s: windows=%d fs=50Hz detrend_slope=%+.3fdB_per_window kept_bins=%s' % (
            path, m['windows'], m['slope'], m['kept']))
        print('%s: detrended_two_sided_3_8Hz p95-p5=%.2fdB peak_to_peak=%.2fdB raw_swing=%.2fdB' % (
            path, m['p95_p5'], m['peak_to_peak'], m['raw_swing']))
