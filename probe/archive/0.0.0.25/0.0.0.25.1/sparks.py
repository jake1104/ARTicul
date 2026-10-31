"""0.0.0.25.1 spark localization probe (no engine change).

Method per task spec:
  crest[i] = peak(|x|, 2ms window) / rms(x, 20ms window), 1ms hop, centered.
  flag[i] = crest[i] > 4 * median(crest[i-100 .. i-1])  (preceding-100ms median)
  group consecutive flagged frames into sparks.
Spark record: start_ms, peak_ms, peak amplitude, duration_ms, dominant octave
  band (band holding the max spark-vs-background energy ratio).
Correlation: distance of spark start to nearest known segment START from
  probe/archive/0.0.0.24/0.0.0.24.1/junctions.txt (blend-zone start == segment
  start in output samples); hit if within +-10ms.
"""
import wave
import numpy as np
import sys

SR = 22050
HOP = int(round(0.001 * SR))          # 1ms hop -> 22 samples
PEAKW = int(round(0.002 * SR))         # 2ms window -> 44 samples
RMSW = int(round(0.020 * SR))         # 20ms window -> 441 samples
MEDN = 100                            # preceding-100ms median (100 frames)
THRESH = 4.0
PEAK_FLOOR = 0.01                     # -40dBFS; ignore flat-digital-silence math

OCTAVES = [
    ("62-125", 62.5, 125.0),
    ("125-250", 125.0, 250.0),
    ("250-500", 250.0, 500.0),
    ("0.5-1k", 500.0, 1000.0),
    ("1-2k", 1000.0, 2000.0),
    ("2-4k", 2000.0, 4000.0),
    ("4-8k", 4000.0, 8000.0),
    ("8k+", 8000.0, 11025.0),
]

# segment START positions in ms (blend-zone start == segment start, output
# timeline; from probe/archive/0.0.0.24/0.0.0.24.1/plan.txt zones + junctions.txt)
BOUNDARIES = {
    "hello": [70.0, 151.0, 213.1],
    "annyeong": [171.0, 215.1, 252.1, 285.1, 365.1, 402.1, 446.1, 556.1,
                 606.2, 664.2, 697.2],
    "yeobo": [35.0, 157.1, 190.1, 285.1, 336.1, 457.1, 490.1],
}


def load_wav(path):
    with wave.open(path, "rb") as w:
        assert w.getnchannels() == 1, w.getnchannels()
        assert w.getframerate() == SR, w.getframerate()
        assert w.getsampwidth() == 2
        n = w.getnframes()
        raw = w.readframes(n)
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
    return x


def crest_track(x):
    n = len(x)
    nfr = 1 + (n - 1) // HOP
    peak = np.empty(nfr)
    rms = np.empty(nfr)
    hp = PEAKW // 2
    hr = RMSW // 2
    ax = np.abs(x)
    for i in range(nfr):
        c = i * HOP
        a = max(0, c - hp)
        b = min(n, c + hp)
        peak[i] = ax[a:b].max() if b > a else 0.0
        a = max(0, c - hr)
        b = min(n, c + hr)
        seg = x[a:b]
        rms[i] = float(np.sqrt((seg * seg).mean())) if b > a else 0.0
    crest = peak / np.maximum(rms, 1e-9)
    return peak, rms, crest


def detect(x):
    peak, rms, crest = crest_track(x)
    nfr = len(crest)
    flag = np.zeros(nfr, dtype=bool)
    for i in range(nfr):
        lo = max(0, i - MEDN)
        med = float(np.median(crest[lo:i])) if i > lo else float(crest[i])
        if med < 1e-9:
            med = 1e-9
        if peak[i] >= PEAK_FLOOR and crest[i] > THRESH * med:
            flag[i] = True
    # group consecutive flagged frames
    sparks = []
    i = 0
    while i < nfr:
        if not flag[i]:
            i += 1
            continue
        j = i
        while j + 1 < nfr and flag[j + 1]:
            j += 1
        s0 = i * HOP
        s1 = min(len(x), j * HOP + HOP)
        seg = np.abs(x[s0:s1])
        k = int(np.argmax(seg))
        peak_pos = s0 + k
        sparks.append({
            "start_ms": s0 / SR * 1000.0,
            "peak_ms": peak_pos / SR * 1000.0,
            "peak_amp": float(seg[k]),
            "dur_ms": float((j - i + 1) * HOP) / SR * 1000.0,
            "peak_pos": peak_pos,
        })
        i = j + 1
    return sparks, peak, rms, crest, flag


def band_energy(xseg, sr=SR, nfft=2048):
    w = np.hanning(len(xseg)) * xseg
    S = np.abs(np.fft.rfft(w, n=nfft)) ** 2
    freqs = np.fft.rfftfreq(nfft, 1.0 / sr)
    out = []
    for _, lo, hi in OCTAVES:
        m = (freqs >= lo) & (freqs < hi)
        out.append(float(S[m].sum()))
    return np.array(out)


def dominant_band(x, peak_pos):
    c = peak_pos
    a = max(0, c - RMSW // 2)
    b = min(len(x), c + RMSW // 2)
    esp = band_energy(x[a:b])
    # background: 100ms immediately before spark start (20ms gap to avoid smear)
    b0 = max(0, a - int(0.020 * SR) - int(0.100 * SR))
    b1 = max(b0 + RMSW, a - int(0.020 * SR))
    ebg = band_energy(x[b0:b1])
    ebg = np.maximum(ebg, 1e-12)
    ratio = esp / ebg
    k = int(np.argmax(ratio))
    return OCTAVES[k][0], float(ratio[k]), float(esp[k] / max(esp.sum(), 1e-18))


def analyze(name, path):
    x = load_wav(path)
    sparks, peak, rms, crest, flag = detect(x)
    bounds = BOUNDARIES[name]
    rows = []
    for s in sparks:
        band, ratio, share = dominant_band(x, s["peak_pos"])
        d = min([abs(s["start_ms"] - b) for b in bounds])
        nearest = min(bounds, key=lambda b: abs(s["start_ms"] - b))
        rows.append({**s, "band": band, "band_ratio": ratio,
                     "band_share": share, "nearest_b": nearest, "dist": d,
                     "hit": d <= 10.0})
    return x, rows


def main():
    files = [("hello", "probe/0.0.0.25.1/hello.wav"),
             ("annyeong", "probe/0.0.0.25.1/annyeong.wav"),
             ("yeobo", "probe/0.0.0.25.1/yeobo.wav")]
    all_rows = {}
    for name, path in files:
        x, rows = analyze(name, path)
        all_rows[name] = (x, rows)
        print("== %s (%d samples, %.1fms, flagged frames %d)" % (
            name, len(x), len(x) / SR * 1000.0, 0))
        print("   start_ms  peak_ms  peak_amp  dur_ms  band  band_x  share   nearest_b  dist  hit")
        for s in rows:
            print("   %8.1f %8.1f  %8.4f  %6.1f  %6s  %6.1f  %.2f  %8.1f %5.1f  %s" % (
                s["start_ms"], s["peak_ms"], s["peak_amp"], s["dur_ms"],
                s["band"], s["band_ratio"], s["band_share"],
                s["nearest_b"], s["dist"], "HIT" if s["hit"] else "miss"))
        hits = sum(1 for s in rows if s["hit"])
        print("   sparks=%d hits=%d hit_rate=%.2f" % (
            len(rows), hits, (hits / len(rows)) if rows else float("nan")))
    tot = sum(len(r) for _, r in all_rows.values())
    hits = sum(1 for _, r in all_rows.values() for s in r if s["hit"])
    print("TOTAL sparks=%d hits=%d hit_rate=%.2f" % (tot, hits, hits / tot if tot else float("nan")))


if __name__ == "__main__":
    main()
