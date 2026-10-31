import math

gains = []
wrms = []
with open('probe/0.0.0.22.3/gain-traj.txt') as f:
    for line in f:
        p = line.split()
        wrms.append(float(p[2].split('=')[1]))
        gains.append(float(p[3].split('=')[1]))

n = len(gains)
fs = 50.0
print('windows=%d window_ms=20 fs=%.0fHz' % (n, fs))
print('gain_dB min=%.2f max=%.2f swing=%.2f' % (min(gains), max(gains), max(gains) - min(gains)))

nfft = 1
while nfft < n:
    nfft *= 2
x = [0.0] * nfft
mean = sum(gains) / n
for i, g in enumerate(gains):
    x[i] = g - mean
re = [0.0] * nfft
im = [0.0] * nfft
for k in range(nfft):
    s_r = 0.0
    s_i = 0.0
    for t in range(nfft):
        a = 2.0 * math.pi * k * t / nfft
        s_r += x[t] * math.cos(a)
        s_i -= x[t] * math.sin(a)
    f = k * fs / nfft
    if 3.0 <= f <= 8.0:
        re[k] = s_r
        im[k] = s_i
bp = []
for t in range(n):
    s = 0.0
    for k in range(nfft):
        a = 2.0 * math.pi * k * t / nfft
        s += (re[k] * math.cos(a) - im[k] * math.sin(a)) / nfft
    bp.append(s)
bp_sorted = sorted(bp)
p5 = bp_sorted[int(0.05 * n)]
p95 = bp_sorted[int(0.95 * n)]
print('syllable_band_3_8Hz p95-p5=%.2fdB peak_to_peak=%.2fdB' % (p95 - p5, max(bp) - min(bp)))
print('verdict_3dB=%s' % ('BREATHING' if (p95 - p5) > 3.0 else 'NO_BREATHING'))

lift = [(i, g) for i, g in enumerate(gains) if g > 6.0]
if lift:
    gs = [g for _, g in lift]
    idx = [i for i, _ in lift]
    diffs = [gs[j + 1] - gs[j] for j in range(len(gs) - 1)]
    print('trough_region windows=%s-%s mean_gain=%.2fdB range=%.2fdB' % (idx[0], idx[-1], sum(gs) / len(gs), max(gs) - min(gs)))
    if diffs:
        m = sum(diffs) / len(diffs)
        sd = (sum((d - m) ** 2 for d in diffs) / len(diffs)) ** 0.5
        print('trough_adjacent_step_std=%.2fdB' % sd)
else:
    print('trough_region none_above_6dB')
deep = max(range(n), key=lambda i: gains[i])
print('max_gain_window=%d gdb=%.2f wrms=%.4f' % (deep, gains[deep], wrms[deep]))
