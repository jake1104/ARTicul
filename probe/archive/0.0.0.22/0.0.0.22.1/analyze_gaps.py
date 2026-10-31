import wave
import numpy as np


SR = 22050


def load(path):
    with wave.open(path) as w:
        n = w.getnframes()
        sr = w.getframerate()
        assert sr == SR, sr
        x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(float) / 32768.0
    return x


def silence_runs(x, thresh_db=-60.0, min_ms=5.0):
    thresh = 10.0 ** (thresh_db / 20.0)
    mask = np.abs(x) < thresh
    min_len = int(round(min_ms * SR / 1000.0))
    runs = []
    i = 0
    n = len(x)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            if j - i >= min_len:
                runs.append((i / SR * 1000.0, (j - i) / SR * 1000.0, j - i))
            i = j
        else:
            i += 1
    return runs


def envelope_dips(x, win_ms=10.0, local_ms=100.0, dip_db=-12.0):
    win = int(round(win_ms * SR / 1000.0))
    nw = len(x) // win
    rms = np.sqrt(np.mean(x[:nw * win].reshape(nw, win) ** 2, axis=1))
    nlocal = int(round(local_ms / win_ms))
    dips = []
    for k in range(nlocal, nw):
        local = np.mean(rms[k - nlocal:k])
        if local < 1e-9:
            continue
        depth = 20.0 * np.log10(max(rms[k], 1e-12) / local)
        if depth < dip_db:
            dips.append((k * win / SR * 1000.0, depth,
                         20.0 * np.log10(max(rms[k], 1e-12))))
    return rms, dips


def crest(x):
    return float(np.max(np.abs(x)) / max(np.sqrt(np.mean(x ** 2)), 1e-12))


def band_split(x):
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    freqs = np.fft.rfftfreq(len(x), 1.0 / SR)
    tot = np.sum(spec)
    lo = np.sum(spec[freqs < 300.0]) / tot
    mid = np.sum(spec[(freqs >= 300.0) & (freqs < 3400.0)]) / tot
    hi = np.sum(spec[freqs >= 4000.0]) / tot
    return lo, mid, hi


for path, label in [("probe/0.0.0.22.1/annyeong.wav", "annyeong"),
                    ("probe/0.0.0.22.1/yeobo.wav", "yeobo")]:
    x = load(path)
    n = len(x)
    dur_ms = n / SR * 1000.0
    peak = float(np.max(np.abs(x)))
    rms = float(np.sqrt(np.mean(x ** 2)))
    print("== %s (%s): n=%d sr=%d dur=%.1fms peak=%.4f rms=%.4f ==="
          % (label, path, n, SR, dur_ms, peak, rms))
    runs = silence_runs(x)
    print("-- silence runs (< -60dBFS, min 5ms): count=%d" % len(runs))
    for s, l, ns in runs:
        print("   start=%.1fms len=%.1fms (%d samples)" % (s, l, ns))
    windows, dips = envelope_dips(x)
    print("-- 10ms-window RMS dips < -12dB vs preceding-100ms mean: count=%d"
          % len(dips))
    for pos, depth, lvl in dips:
        print("   pos=%.1fms depth=%+.1fdB winlvl=%.1fdBFS" % (pos, depth, lvl))
    print("-- crest peak/RMS global=%.2f" % crest(x))
    thirds = np.array_split(x, 3)
    for t, seg in enumerate(thirds):
        print("   third%d crest=%.2f rms=%.4f" % (t, crest(seg),
              float(np.sqrt(np.mean(seg ** 2)))))
    lo, mid, hi = band_split(x)
    print("-- band energy: 0-300Hz=%.3f 300-3400Hz=%.3f 4k+Hz=%.3f (rest 3.4-4k=%.3f)"
          % (lo, mid, hi, 1.0 - lo - mid - hi))
    halves = 20 * np.log10(np.sqrt(np.mean(x[n // 2:] ** 2))
                           / max(np.sqrt(np.mean(x[:n // 2] ** 2)), 1e-9))
    print("-- halves=%+.2fdB" % halves)
    print("")
