import numpy as np, wave
import os
for label, path in [("annyeong","demo/annyeonghaseyo.wav"),("yeobo","demo/yeoboseyo.wav"),("hello","demo/hello.wav")]:
    w = wave.open(path,'rb'); n = w.getnframes(); x = np.frombuffer(w.readframes(n),dtype=np.int16).astype(np.float64)/32767.0
    n3 = n//3
    for i,seg in enumerate([x[0:n3],x[n3:2*n3],x[2*n3:]]):
        r = float(np.sqrt((seg*seg).mean())); print('%s third%d rms=%.4f (%.2fdBFS)'%(label,i,r,20*np.log10(max(r,1e-9))))
