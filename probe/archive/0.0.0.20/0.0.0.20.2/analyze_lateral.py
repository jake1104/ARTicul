import wave, struct, sys
import numpy as np

PATH = sys.argv[1] if len(sys.argv) > 1 else "la-green.wav"
SR = 22050
N_FFT = 8192

with wave.open(PATH, "rb") as w:
    assert w.getnchannels() == 1 and w.getsampwidth() == 2 and w.getframerate() == SR
    n = w.getnframes()
    raw = w.readframes(n)
x = np.array(struct.unpack("<%dh" % n, raw), dtype=np.float64) / 32768.0
print("samples=%d total_ms=%.2f sr=%d" % (n, n / SR * 1000.0, SR))

seg = x[110:1258]
print("window samples 110-1258 N=%d" % len(seg))

W = np.hanning(len(seg))
S = np.abs(np.fft.rfft(seg * W, n=N_FFT)) ** 2
freqs = np.fft.rfftfreq(N_FFT, 1.0 / SR)

SS = np.zeros_like(S)
for k in range(len(S)):
    a = max(0, k - 12)
    b = min(len(S), k + 13)
    SS[k] = S[a:b].mean()

def med(S_, lo, hi):
    m = (freqs >= lo) & (freqs < hi)
    return float(10.0 * np.log10(np.median(S_[m])))

edge = med(S, 2000.0, 2300.0)
core = med(S, 2470.0, 2530.0)
print("edge 2000-2300 raw: %.2f dB" % edge)
print("core 2470-2530 raw: %.2f dB" % core)
print("notch depth (edge-core): %.2f dB" % (edge - core))

def peak_near(S_, target, tol):
    lo = int(np.floor((target - tol) / SR * N_FFT))
    hi = int(np.ceil((target + tol) / SR * N_FFT))
    band = S_[lo:hi + 1]
    srt = np.sort(band)
    median = float(srt[len(srt) // 2])
    best = None
    for k in range(lo + 2, hi - 1):
        if S_[k] > S_[k - 1] and S_[k] > S_[k - 2] and S_[k] >= S_[k + 1] and S_[k] >= S_[k + 2] and S_[k] > 3.0 * median:
            if best is None or S_[k] > best[0]:
                best = (S_[k], k)
    if best is None:
        return None
    return best[1] * SR / N_FFT

f1 = peak_near(SS, 300.0, 100.0)
f2 = peak_near(SS, 1400.0, 200.0)
print("F1 peak: %s" % ("%.1f Hz" % f1 if f1 else "none"))
print("F2 peak: %s" % ("%.1f Hz" % f2 if f2 else "none"))
