import wave
import numpy as np

SR = 22050
WIN = int(round((10.0 / 1000.0) * SR))
CUT = 0.985


def load(path):
    with wave.open(path, "rb") as w:
        n = w.getnframes()
        data = w.readframes(n)
    return np.frombuffer(data, dtype=np.int16).astype(np.float64) / 32767.0


def autocorr_peak(x, f_lo=80.0, f_hi=300.0):
    v = x - x.mean()
    denom = float((v * v).sum())
    if denom <= 1e-12:
        return 0, 0.0
    l0 = int(SR / f_hi)
    l1 = int(SR / f_lo)
    best_l, best_r = 0, -2.0
    for lag in range(l0, l1 + 1):
        if lag >= len(v):
            break
        r = float((v[:len(v) - lag] * v[lag:]).sum()) / denom
        if r > best_r:
            best_r, best_l = r, lag
    return best_l, best_r


def hf_frac(x):
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    freqs = np.fft.rfftfreq(len(x), 1.0 / SR)
    tot = float(spec.sum())
    return float(spec[freqs >= 4000.0].sum()) / tot if tot > 0 else 0.0


def rms(v):
    return float(np.sqrt((v * v).mean())) if len(v) else 0.0


def report(tag, x, pos):
    w = x[pos:pos + WIN]
    a = np.abs(w)
    d_all = int(np.argmax(a))
    mask = a < CUT
    uc = a[mask]
    d_uc = None
    peak_uc = 0.0
    if len(uc):
        peak_uc = float(uc.max())
        d_uc = int(np.argmax(np.where(mask, a, -1.0)))
    clamped_idx = [int(i) for i in np.where(a >= CUT)[0]]
    top5 = [int(i) for i in np.argsort(a)[-5:]][::-1]
    pre = x[max(0, pos - WIN):pos]
    h1, h2 = w[:WIN // 2], w[WIN // 2:]
    lag, r = autocorr_peak(w)
    print("== %s pos=%d" % (tag, pos))
    print("   peak_all=%.4f d_all=%d (%.2f ms)" % (float(a.max()), d_all, d_all / SR * 1000.0))
    print("   peak_unclamped=%.4f d_uc=%s clamped_idx=%s" % (peak_uc, d_uc, clamped_idx))
    print("   top5 offsets=%s vals=%s" % (top5, [round(float(a[i]), 4) for i in top5]))
    print("   rms pre10ms=%.4f win_h1=%.4f win_h2=%.4f (h2/h1=%+.2fdB pre/win=%+.2fdB)"
          % (rms(pre), rms(h1), rms(h2),
             20 * np.log10(max(rms(h2), 1e-9) / max(rms(h1), 1e-9)),
             20 * np.log10(max(rms(pre), 1e-9) / max(rms(w), 1e-9))))
    print("   autocorr 80-300Hz: lag=%d f=%.1fHz r=%.3f" % (lag, SR / lag if lag else 0.0, r))
    print("   hf_frac(4k+): pre=%.3f h1=%.3f h2=%.3f" % (hf_frac(pre), hf_frac(h1), hf_frac(h2)))


new = load("probe/0.0.0.33.2/annyeonghaseyo.wav")
old = load("demo/annyeonghaseyo.wav")
print("lengths: new=%d old=%d win=%d" % (len(new), len(old), WIN))
report("NEW s9 s->e", new, 15021)
report("OLD s9 s->e", old, 13366)
report("NEW s8 h\\-a->s onset (control: /s/ attack)", new, 13918)
report("OLD s8 h-a->s onset (control)", old, 12263)
