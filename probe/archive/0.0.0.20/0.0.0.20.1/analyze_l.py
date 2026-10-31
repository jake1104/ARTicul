import wave, struct, sys
import numpy as np

PATH = sys.argv[1] if len(sys.argv) > 1 else "hello.wav"
SR = 22050

with wave.open(PATH, "rb") as w:
    assert w.getnchannels() == 1 and w.getsampwidth() == 2 and w.getframerate() == SR, (
        w.getnchannels(), w.getsampwidth(), w.getframerate())
    n = w.getnframes()
    raw = w.readframes(n)
x = np.array(struct.unpack("<%dh" % n, raw), dtype=np.float64) / 32768.0
print("samples=%d total_ms=%.2f sr=%d" % (n, n / SR * 1000.0, SR))

# Nominal l-window from known plan: h 78ms + E 89ms = 167ms start, l 70ms -> 237ms end.
L0_MS, L1_MS = 167.0, 237.0
L0 = int(L0_MS / 1000.0 * SR)
L1 = int(L1_MS / 1000.0 * SR)
print("l-window nominal: %.1f-%.1f ms (samples %d-%d)" % (L0_MS, L1_MS, L0, L1))

def spectrum(seg, nfft=4096):
    w_ = np.hanning(len(seg))
    S = np.fft.rfft(seg * w_, n=nfft)
    freqs = np.fft.rfftfreq(nfft, 1.0 / SR)
    mag = np.abs(S) / (w_.sum() / 2.0)
    db = 20.0 * np.log10(mag + 1e-12)
    return freqs, db

def peak_in(freqs, db, lo, hi):
    m = (freqs >= lo) & (freqs <= hi)
    f = freqs[m]; d = db[m]
    i = int(np.argmax(d))
    return float(f[i]), float(d[i])

def min_in(freqs, db, lo, hi):
    m = (freqs >= lo) & (freqs <= hi)
    f = freqs[m]; d = db[m]
    i = int(np.argmin(d))
    return float(f[i]), float(d[i])

# Interior steady 40ms: middle of window (15ms margins each side).
C0_MS, C1_MS = L0_MS + 15.0, L1_MS - 15.0
c0 = int(C0_MS / 1000.0 * SR); c1 = int(C1_MS / 1000.0 * SR)
seg = x[c0:c1]
print("interior steady: %.1f-%.1f ms (N=%d)" % (C0_MS, C1_MS, len(seg)))
freqs, db = spectrum(seg)

f1, f1db = peak_in(freqs, db, 200.0, 600.0)
f2, f2db = peak_in(freqs, db, 900.0, 1900.0)
f3, f3db = peak_in(freqs, db, 2200.0, 3400.0)
print("F1 peak: %.1f Hz (%.2f dB)" % (f1, f1db))
print("F2 peak: %.1f Hz (%.2f dB)" % (f2, f2db))
print("F3 peak: %.1f Hz (%.2f dB)" % (f3, f3db))

# F1 bandwidth: -3dB width around F1 peak.
m = (freqs >= 150.0) & (freqs <= 800.0)
f = freqs[m]; d = db[m]
ipk = int(np.argmax(d))
thr = d[ipk] - 3.0
lo_i = ipk
while lo_i > 0 and d[lo_i] > thr:
    lo_i -= 1
hi_i = ipk
while hi_i < len(d) - 1 and d[hi_i] > thr:
    hi_i += 1
print("F1 bandwidth (-3dB): %.1f Hz (%.1f-%.1f Hz)" % (f[hi_i] - f[lo_i], f[lo_i], f[hi_i]))

# Notch depth in 2-3kHz vs neighboring peaks.
# Robust metric: narrowband bins show inter-harmonic gaps (F0~130Hz vs 5.4Hz
# bins), so compare 200Hz-band MEDIAN envelope levels instead. A lateral
# antiformant zero would carve a wide valley between the F2 (~1400) and
# F3 (~2800) regions; depth = min(flanks) - valley floor on medians.
def band_med(lo, hi):
    m = (freqs >= lo) & (freqs < hi)
    return float(np.median(db[m]))

f2med = band_med(1200.0, 1600.0)
vmed = band_med(1900.0, 2500.0)
f3med = band_med(2500.0, 2900.0)
depth = min(f2med, f3med) - vmed
print("F2-region (1.2-1.6kHz) median: %.2f dB" % f2med)
print("valley (1.9-2.5kHz) median: %.2f dB" % vmed)
print("F3-region (2.5-2.9kHz) median: %.2f dB" % f3med)
print("notch depth (median envelope): %.2f dB" % depth)
# Narrowband numbers kept for the record (harmonic-gap contaminated).
fmin, mindb = min_in(freqs, db, 2000.0, 3000.0)
plo, plodb = peak_in(freqs, db, 1000.0, 2000.0)
phi, phidb = peak_in(freqs, db, 2500.0, 3400.0)
depth_lo = plodb - mindb
depth_hi = phidb - mindb
print("2-3kHz minimum: %.1f Hz (%.2f dB)" % (fmin, mindb))
print("neighbor peak lo: %.1f Hz (%.2f dB)" % (plo, plodb))
print("neighbor peak hi: %.1f Hz (%.2f dB)" % (phi, phidb))
print("notch depth vs lo: %.2f dB" % depth_lo)
print("notch depth vs hi: %.2f dB" % depth_hi)
print("notch depth (min side): %.2f dB" % min(depth_lo, depth_hi))

# Steady-state length via RMS plateau: 5ms frames over l-window + margins.
def rms_frames(x_, fms=5.0):
    fl = int(fms / 1000.0 * SR)
    out = []
    for s in range(0, len(x_) - fl + 1, fl):
        out.append(float(np.sqrt(np.mean(x_[s:s + fl] ** 2))))
    return np.array(out), fl

pad0 = int((L0_MS - 20.0) / 1000.0 * SR); pad1 = int((L1_MS + 20.0) / 1000.0 * SR)
reg = x[pad0:pad1]
rms, fl = rms_frames(reg)
rmsdb = 20.0 * np.log10(rms + 1e-12)
# interior frames: those fully inside [L0, L1]
start_idx = int(round((L0 - pad0) / fl))
end_idx = int(round((L1 - pad0) / fl))
interior = rmsdb[start_idx:end_idx]
med = float(np.median(interior))
plateau = np.abs(interior - med) <= 1.0
# longest contiguous run
best = cur = 0
for v in plateau:
    cur = cur + 1 if v else 0
    best = max(best, cur)
print("RMS plateau: median %.2f dBFS, longest +-1dB run %d frames = %.1f ms" % (
    med, best, best * 5.0))

# Boundary slopes: 2ms RMS envelope, dB change per 10ms across E-l and l-o edges.
rms2, fl2 = rms_frames(x, fms=2.0)
rdb2 = 20.0 * np.log10(rms2 + 1e-12)
t2 = (np.arange(len(rdb2)) * 2.0) + 1.0  # frame center ms
def slope_at(edge_ms, side_lo, side_hi):
    # slope = (level after - level before) per 10ms, using 10ms means each side
    def mean_db(a, b):
        m_ = (t2 >= a) & (t2 < b)
        return float(np.mean(rdb2[m_]))
    before = mean_db(edge_ms - 10.0, edge_ms)
    after = mean_db(edge_ms, edge_ms + 10.0)
    return before, after, after - before
for edge, name in ((L0_MS, "E-l"), (L1_MS, "l-o")):
    b, a, s = slope_at(edge, None, None)
    print("%s edge %.1f ms: before %.2f dB, after %.2f dB, slope %+.2f dB/10ms" % (
        name, edge, b, a, s))
