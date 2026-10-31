import wave
import numpy as np

FILES = {
    "hello": "demo/hello.wav",
    "regression-a": "probe/archive/0.0.0.17/0.0.0.17.5/regression-a.wav",
}

SIL_THRESH = 0.02

def analyze(path):
    with wave.open(path, "rb") as w:
        nch, sw, sr, n, _, _ = w.getparams()
        raw = w.readframes(n)
    dt = {1: np.int8, 2: np.int16, 4: np.int32}[sw]
    x = np.frombuffer(raw, dtype=dt).astype(np.float64)
    if nch > 1:
        x = x.reshape(-1, nch).mean(axis=1)
    peak_norm = np.abs(x).max() / float(-np.iinfo(dt).min)
    x = x / float(-np.iinfo(dt).min)
    n = x.shape[0]
    dur = n / sr
    rms = float(np.sqrt(np.mean(x ** 2)))
    dc = float(np.mean(x))
    clip = float(np.mean(np.abs(x) >= 0.999))
    zcr = float(np.sum(x[1:] * x[:-1] < 0) / max(1, n - 1))
    win = sr // 10
    nwin = max(1, n // win)
    wrms = [float(np.sqrt(np.mean(x[i * win:(i + 1) * win] ** 2))) for i in range(nwin)]
    sil = float(np.mean(np.array(wrms) < SIL_THRESH))
    X = np.abs(np.fft.rfft(x * np.hanning(n)))
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    tot = float(np.sum(X ** 2))
    cent = float(np.sum(freqs * X) / max(1e-12, np.sum(X)))
    b1 = float(np.sum(X[(freqs < 300)] ** 2) / tot)
    b2 = float(np.sum(X[(freqs >= 300) & (freqs < 3400)] ** 2) / tot)
    b3 = float(np.sum(X[freqs >= 4000] ** 2) / tot)
    return dict(sr=sr, n=n, dur=dur, peak=peak_norm, rms=rms, dc=dc,
                clip=clip, zcr=zcr, cent=cent, b1=b1, b2=b2, b3=b3,
                sil=sil, wrms=wrms)

rows = {k: analyze(p) for k, p in FILES.items()}

def fmt_row(r):
    return (f"sr={r['sr']} frames={r['n']} dur={r['dur']:.3f}s "
            f"peak={r['peak']:.4f} rms={r['rms']:.4f} dc={r['dc']:+.5f} "
            f"clip={r['clip']:.4f} zcr={r['zcr']:.4f} cent={r['cent']:.1f}Hz "
            f"b0-300={r['b1']:.3f} b300-3400={r['b2']:.3f} b4k+={r['b3']:.3f} "
            f"sil<{SIL_THRESH}={r['sil']:.3f}")

lines = []
lines.append("metric | hello (demo/hello.wav) | regression-a (probe/.../0.0.0.17.5/regression-a.wav)")
for k in ("hello", "regression-a"):
    lines.append(f"{k} | {fmt_row(rows[k])}")
for k in ("hello", "regression-a"):
    wr = rows[k]["wrms"]
    lines.append(f"{k} 100ms RMS ({len(wr)} windows): " + " ".join(f"{v:.3f}" for v in wr))
out = "\n".join(lines) + "\n"
print(out)
