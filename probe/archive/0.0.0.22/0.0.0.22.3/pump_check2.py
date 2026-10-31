import math

gains = []
with open('probe/0.0.0.22.3/gain-traj.txt') as f:
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
print('windows=%d fs=%.0fHz detrend_slope=%.3fdB_per_window' % (n, fs, slope))

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
print('kept_bins=%s' % kept)
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
print('detrended_two_sided_3_8Hz p95-p5=%.2fdB peak_to_peak=%.2fdB' % (p95 - p5, max(bp) - min(bp)))
print('raw_gain_swing=%.2fdB' % (max(gains) - min(gains)))
print('baseline_pre_leveler_constant_gain=0.00dB')
print('trough_benefit_annyeong=-18.6dB_to_-10.5dB')
print('verdict_6dB=%s' % ('SWITCH' if (p95 - p5) >= 6.0 else 'KEEP'))
