import numpy as np
from scipy.signal import welch

sr = 22050
f0 = 100.0
oq = 0.6
dur = 0.5
n = int(dur * sr)
t = np.arange(n) / sr
phase = (t * f0) % 1.0
x = np.clip(phase / oq, 0.0, 1.0)
pulse = np.where(phase < oq, 0.5 - 0.5 * np.cos(2 * np.pi * x), 0.0)
freqs, psd = welch(pulse, fs=sr, nperseg=8192)
mask = (freqs >= 100) & (freqs <= 4000)
xs = np.log2(freqs[mask])
ys = 10 * np.log10(psd[mask] + 1e-12)
slope, _ = np.polyfit(xs, ys, 1)
print(f"slope_db_per_oct={slope:.2f}")
print(f"in_expected_range={-20.0 <= slope <= -4.0}")
