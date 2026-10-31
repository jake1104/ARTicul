import subprocess
import sys
import numpy as np
import wave

EXE = "target/release/articul.exe"

JOBS = [
    (["%ho", "config/korean-voice.toml", "probe/0.0.0.35.2/korean_o.wav"], "korean-o"),
]

for (text, voice, out), label in JOBS:
    p = subprocess.run([EXE, "synthesize", "--text", text, "--voice", voice, "--out", out],
                       capture_output=True, text=True)
    print("== %s: rc=%d stdout=%r stderr=%r" % (label, p.returncode, p.stdout.strip(), p.stderr.strip()))
    if p.returncode != 0:
        sys.exit(1)

SR = 22050
with wave.open("probe/0.0.0.35.2/korean_o.wav", "rb") as w:
    n = w.getnframes()
    raw = w.readframes(n)
x = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32767.0
print("samples", len(x))

NFFT = 8192
seg = x[len(x)//4:len(x)//4 + len(x)//2]
sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n=NFFT)) ** 2
freqs = np.fft.rfftfreq(NFFT, 1.0/SR)
pw = sp / np.maximum(sp[100:3000].mean() if len(sp) > 3000 else sp.mean(), 1e-12)
for lo, hi in [(600.0, 900.0), (703.0, 777.0)]:
    m = (freqs >= lo) & (freqs <= hi)
    idx = np.argmax(sp[m])
    f = freqs[m][idx]
    print("band %.0f-%.0f peak %.1fHz mag %.4f pwratio %.3f" % (lo, hi, f, sp[m][idx], pw[m][idx]))
ref = np.median(sp[(freqs >= 300.0) & (freqs <= 3000.0)])
print("ref-median", ref)
order = np.argsort(sp[(freqs >= 703.0) & (freqs <= 777.0)])[::-1][:5]
sub = sp[(freqs >= 703.0) & (freqs <= 777.0)]
ff = freqs[(freqs >= 703.0) & (freqs <= 777.0)]
for i in order:
    print("cand %.1fHz mag %.4f ratio %.3f" % (ff[i], sub[i], sub[i]/ref))
print("ALL OK")
