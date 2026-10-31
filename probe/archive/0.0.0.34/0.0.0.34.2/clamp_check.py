import wave
import numpy as np

for label, path in [
    ("annyeong", "probe/0.0.0.34.2/annyeonghaseyo-korean.wav"),
    ("yeobo", "probe/0.0.0.34.2/yeoboseyo-korean.wav"),
]:
    w = wave.open(path, "rb")
    n = w.getnframes()
    x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float64) / 32767.0
    idx = np.where(np.abs(x) >= 0.985)[0]
    print(label, "clamp_count=", len(idx), "positions_ms=", [round(float(i) / 22050 * 1000, 1) for i in idx])
