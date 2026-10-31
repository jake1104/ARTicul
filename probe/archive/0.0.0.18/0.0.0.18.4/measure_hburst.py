import math
import wave

import numpy as np

SR = 22050
WAV = "probe/0.0.0.18.4/hello-hburst.wav"
OUT = "probe/0.0.0.18.4/h-burst.txt"

DURS_MS = [78, 89, 50, 148, 83]
FADES = [0, 176, 176, 176, 1102]

with wave.open(WAV, "rb") as w:
    assert w.getnchannels() == 1
    assert w.getsampwidth() == 2
    assert w.getframerate() == SR
    raw = w.readframes(w.getnframes())

x = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
n = x.shape[0]

lens = [int(d * SR / 1000.0 + 0.5) for d in DURS_MS]
starts = [0] * len(lens)
for i in range(1, len(lens)):
    starts[i] = starts[i - 1] + lens[i - 1] - FADES[i]
total = sum(lens) - sum(FADES)
assert n == total, (n, total)

h_win = x[0:lens[0]]
o_pure_start = starts[3]
o_pure_end = starts[4]
o_mid = (o_pure_start + o_pure_end) // 2
half = int(40 * SR / 1000.0)
o_win = x[o_mid - half:o_mid + half]


def stats(v):
    peak = float(np.max(np.abs(v)))
    rms = float(np.sqrt(np.mean(v * v)))
    return peak, 20.0 * math.log10(max(peak, 1e-12)), rms, 20.0 * math.log10(max(rms, 1e-12))


h_peak, h_peak_db, h_rms, h_rms_db = stats(h_win)
o_peak, o_peak_db, o_rms, o_rms_db = stats(o_win)
f_peak, f_peak_db, f_rms, f_rms_db = stats(x)

lines = [
    "h-burst measurement: hello `hE \"loU`, post-18.4 release binary, sr 22050",
    f"wav samples: {n} (nominal {total})",
    f"h-interior window: [0..{lens[0]}) = first 78ms",
    f"stressed-o interior window: [{o_mid - half}..{o_mid + half}) = middle 80ms of pure-o [{o_pure_start}..{o_pure_end})",
    "whole-file window: [0..%d)" % n,
    "",
    "window            peak_lin   peak_dBFS   rms_lin    rms_dBFS",
    f"h-interior        {h_peak:.6f}   {h_peak_db:7.2f}   {h_rms:.6f}   {h_rms_db:7.2f}",
    f"stressed-o        {o_peak:.6f}   {o_peak_db:7.2f}   {o_rms:.6f}   {o_rms_db:7.2f}",
    f"whole-file        {f_peak:.6f}   {f_peak_db:7.2f}   {f_rms:.6f}   {f_rms_db:7.2f}",
    "",
    f"margin whole-peak minus h-peak: {f_peak_db - h_peak_db:.2f} dB",
    f"margin o-peak minus h-peak: {o_peak_db - h_peak_db:.2f} dB",
    f"margin o-rms minus h-rms: {o_rms_db - h_rms_db:.2f} dB",
    f"whole-file peak setter: {'h-interior' if abs(f_peak - h_peak) < 1e-12 else ('stressed-o' if abs(f_peak - o_peak) < 1e-12 else 'other')}",
]
text = "\n".join(lines) + "\n"
with open(OUT, "w") as f:
    f.write(text)
print(text, end="")
