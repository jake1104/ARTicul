import wave
import numpy as np

SR = 22050
FILES = {
    "hello": "probe/0.0.0.23.1/hello.wav",
    "annyeong": "probe/0.0.0.23.1/annyeong.wav",
    "yeobo": "probe/0.0.0.23.1/yeobo.wav",
}
KNOWN = {
    "hello": None,
    "annyeong": (610.0, 680.0),
    "yeobo": (340.0, 450.0),
}


def load(path):
    with wave.open(path) as w:
        n = w.getnframes()
        assert w.getframerate() == SR
        x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(float) / 32768.0
    return x


def envelope(x, win_ms=10.0):
    win = int(round(win_ms * SR / 1000.0))
    nw = len(x) // win
    rms = np.sqrt(np.mean(x[:nw * win].reshape(nw, win) ** 2, axis=1))
    t = (np.arange(nw) * win) / SR * 1000.0
    return t, rms


def deepest_trough(t, rms, total_ms, fade_ms=150.0, dip_db=-8.0, local_ms=100.0):
    nlocal = int(round(local_ms / 10.0))
    depth = np.full_like(rms, np.nan)
    for k in range(nlocal, len(rms)):
        local = np.mean(rms[k - nlocal:k])
        if local > 1e-9:
            depth[k] = 20.0 * np.log10(max(rms[k], 1e-12) / local)
    cut = total_ms - fade_ms
    best = None
    k = nlocal
    while k < len(rms):
        if t[k] < cut and not np.isnan(depth[k]) and depth[k] < dip_db:
            j = k
            while (j + 1 < len(rms) and t[j + 1] < cut
                   and not np.isnan(depth[j + 1]) and depth[j + 1] < dip_db):
                j += 1
            run_min = float(np.min(depth[k:j + 1]))
            span = (float(t[k]), float(t[j] + 10.0), run_min)
            if best is None or run_min < best[2]:
                best = span
            k = j + 1
        else:
            k += 1
    return best, depth


def subwin_bands(x, t0_ms, t1_ms, sub_ms=20.0):
    sub = int(round(sub_ms * SR / 1000.0))
    i0 = int(round(t0_ms * SR / 1000.0))
    i1 = int(round(t1_ms * SR / 1000.0))
    tot, sp, hf = [], [], []
    for s in range(i0, i1, sub):
        seg = x[s:s + sub]
        if len(seg) < sub // 2:
            continue
        seg = seg * np.hanning(len(seg))
        rms_t = float(np.sqrt(np.mean(seg ** 2)))
        spec = np.abs(np.fft.rfft(seg)) ** 2
        freqs = np.fft.rfftfreq(len(seg), 1.0 / SR)
        ptot = float(np.sum(spec)) + 1e-18
        f_sp = float(np.sum(spec[(freqs >= 300) & (freqs <= 3400)])) / ptot
        f_hf = float(np.sum(spec[freqs >= 4000])) / ptot
        tot.append(rms_t)
        sp.append(rms_t * np.sqrt(f_sp))
        hf.append(rms_t * np.sqrt(f_hf))
    return np.array(tot), np.array(sp), np.array(hf)


def pearson(a, b):
    a = a - a.mean()
    b = b - b.mean()
    d = np.sqrt(np.sum(a ** 2) * np.sum(b ** 2))
    return float(np.sum(a * b) / d) if d > 0 else float("nan")


for name, path in FILES.items():
    x = load(path)
    total_ms = len(x) / SR * 1000.0
    t, rms = envelope(x)
    best, depth = deepest_trough(t, rms, total_ms)
    print("== %s n=%d dur=%.1fms" % (name, len(x), total_ms))
    print("known window ms: %s" % (str(KNOWN[name]),))
    if best is None:
        print("no trough below -8dB outside final fade")
        continue
    print("deepest non-fade trough: %.1f-%.1fms mindepth=%.2fdB" % best)
    wins = [("detected", best[0], best[1])]
    if KNOWN[name] is not None:
        wins.append(("known", KNOWN[name][0], KNOWN[name][1]))
    for label, t0, t1 in wins:
        tot, sp, hf = subwin_bands(x, t0, t1)
        n = len(tot)
        r_hf = pearson(hf, tot)
        r_sp = pearson(sp, tot)
        f_sp = float(np.mean(sp ** 2) / (np.mean(tot ** 2) + 1e-18))
        f_hf = float(np.mean(hf ** 2) / (np.mean(tot ** 2) + 1e-18))
        print("[%s %.0f-%.0fms n=%d] r(HF,total)=%.3f r(speech,total)=%.3f "
              "HFfrac=%.3f speechfrac=%.3f HFdBFS=%.1f speechdBFS=%.1f" % (
                  label, t0, t1, n, r_hf, r_sp, f_hf, f_sp,
                  20 * np.log10(np.sqrt(np.mean(hf ** 2)) + 1e-12),
                  20 * np.log10(np.sqrt(np.mean(sp ** 2)) + 1e-12)))
