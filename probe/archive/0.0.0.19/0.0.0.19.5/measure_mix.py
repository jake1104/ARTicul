import os
import subprocess
import sys
import tempfile
import wave

import numpy as np

SR = 22050
F0 = 120.0
VOICE_CUTOFF_HZ = 300.0
BAND_FMIN_HZ = 80.0
BAND_FMAX_HZ = 300.0
BROAD_FMIN_HZ = 60.0
BROAD_FMAX_HZ = 300.0

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BIN = os.path.join(REPO, "target", "release", "articul.exe")
if not os.path.exists(BIN):
    BIN = os.path.join(REPO, "target", "release", "articul")
VOICE = os.path.join(REPO, "config", "default-voice.toml")
TMPDIR = r"C:\Users\jake1\AppData\Local\Temp\opencode"


def render(text):
    os.makedirs(TMPDIR, exist_ok=True)
    fd, path = tempfile.mkstemp(suffix=".wav", dir=TMPDIR)
    os.close(fd)
    cmd = [BIN, "synthesize", "--text", text, "--voice", VOICE,
           "--out", path, "--f0", str(F0)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("synth failed: " + r.stderr)
    return path


def load(path):
    with wave.open(path) as w:
        sr = w.getframerate()
        n = w.getnframes()
        raw = w.readframes(n)
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
    return sr, n, x


def voice_bar(x):
    a = 1.0 - np.exp(-2.0 * np.pi * VOICE_CUTOFF_HZ / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, s in enumerate(x):
        acc += a * (s - acc)
        y[i] = acc
    return y


def autocorr_peak(x, fmin, fmax):
    v = x - np.mean(x)
    e0 = float(np.dot(v, v))
    if e0 <= 1e-12:
        return 0.0, 0
    lo = max(1, int(np.ceil(SR / fmax)))
    hi = min(len(v) - 1, int(np.floor(SR / fmin)))
    best, blag = 0.0, 0
    for lag in range(lo, hi + 1):
        r = float(np.dot(v[:len(v) - lag], v[lag:]) / e0)
        if r > best:
            best, blag = r, lag
    return best, blag


def above_4k_fraction(x):
    n = len(x)
    w = 0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(n) / n)
    spec = np.fft.rfft(x * w)
    p = np.abs(spec) ** 2
    f = np.fft.rfftfreq(n, 1.0 / SR)
    return float(np.sum(p[f >= 4000.0]) / max(np.sum(p), 1e-12))


def measure(text):
    path = render(text)
    try:
        sr, n, x = load(path)
    finally:
        os.remove(path)
    assert sr == SR
    vb = voice_bar(x)
    vpeak, vlag = autocorr_peak(vb, BAND_FMIN_HZ, BAND_FMAX_HZ)
    bpeak, blag = autocorr_peak(x, BROAD_FMIN_HZ, BROAD_FMAX_HZ)
    hf = above_4k_fraction(x)
    return {
        "text": text,
        "n": n,
        "voice_peak": vpeak,
        "voice_lag": vlag,
        "broad_peak": bpeak,
        "broad_lag": blag,
        "hf": hf,
    }


def main():
    rows = [measure("z"), measure("s")]
    for m in rows:
        print("sym={text} n={n} voice_peak={voice_peak:.4f}@{voice_lag} "
              "broad_peak={broad_peak:.4f}@{broad_lag} hf={hf:.4f}".format(**m))


if __name__ == "__main__":
    sys.exit(main())
