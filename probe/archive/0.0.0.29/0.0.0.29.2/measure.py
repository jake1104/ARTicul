import math, re, struct, wave
import numpy as np
SR=22050
FWIN=441
HOP=220
NFFT=2048
EDGE=220
PLAN="probe/archive/0.0.0.24/0.0.0.24.1/plan.txt"
FILES={"hello":"probe/0.0.0.29.2/hello.wav","annyeong":"probe/0.0.0.29.2/annyeong.wav","yeobo":"probe/0.0.0.29.2/yeobo.wav"}
LABELS={"hello":["h","E","l","o","U"],"annyeong":["a","n","n","j","V","N","h","a","s","e","j","o"],"yeobo":["j","V","b","o","s","e","j","o"]}
FRIC={"s","h"}
def load(p):
    import wave,struct
    w=wave.open(p,"rb");n=w.getnframes();raw=w.readframes(n)
    return np.array(struct.unpack("<%dh"%n,raw),dtype=np.float64)/32767.0
def parse(p):
    demos={};cur=None
    import re
    for line in open(p,encoding="utf-8"):
        line=line.rstrip("\n")
        m=re.match(r"== (\w+) ::",line)
        if m:cur=m.group(1);demos[cur]={"units":[],"bounds":[],"outlen":0,"lens":[],"fades":[],"work":[]};continue
        m=re.match(r"work_units=(.*) lens=\[(.*)\] fades=\[(.*)\] predicted_out_len=(\d+)",line)
        if m and cur is not None:
            demos[cur]["work"]=[[int(v) for v in g.strip("[]").split(",") if v.strip()!=""] for g in m.group(1).split("] [")]
            demos[cur]["lens"]=[int(v) for v in m.group(2).split(",")]
            demos[cur]["fades"]=[int(v) for v in m.group(3).split(",")]
            demos[cur]["outlen"]=int(m.group(4));continue
        m=re.match(r"b(\d+) between u(\d+)\(.*\)->u(\d+)\(.*\) type=(\S+) zone=\[(\d+), (\d+)\) n=(\d+) gain_step=([0-9.]+)dB f0_step=([0-9.\-]+)st",line)
        if m and cur is not None:
            demos[cur]["bounds"].append({"b":int(m.group(1)),"prev":int(m.group(2)),"nxt":int(m.group(3)),"z0":int(m.group(5)),"z1":int(m.group(6))})
    return demos
def out_spans(d):
    starts=[];acc=0
    for k,ln in enumerate(d["lens"]):
        starts.append(acc)
        acc+=ln if k+1==len(d["lens"]) else ln-d["fades"][k+1]
    return list(zip(starts,[s+ln for s,ln in zip(starts,d["lens"])]))
def pick(pw,flo,fhi,fmin=None):
    freqs=np.fft.rfftfreq(NFFT,1.0/SR)
    lo=int(np.searchsorted(freqs,flo));hi=int(np.searchsorted(freqs,fhi))
    idx=int(np.argmax(pw[lo:hi]))+lo
    if fmin is not None:
        lo2=max(idx,int(np.searchsorted(freqs,fmin)))
        if lo2<hi:idx=int(np.argmax(pw[lo2:hi]))+lo2
    if 0<idx<len(pw)-1:
        a,b,c=pw[idx-1],pw[idx],pw[idx+1]
        d=(a-c)/(2.0*(a-2.0*b+c)) if (a-2*b+c)!=0 else 0.0
        d=max(-0.5,min(0.5,d))
        return (idx+d)*SR/NFFT
    return idx*SR/NFFT
def frame_f2(x,p):
    fr=x[p:p+FWIN]*np.hanning(FWIN)
    pw=np.abs(np.fft.rfft(fr,NFFT))**2
    f1=pick(pw,200,1000)
    return pick(pw,800,2800,fmin=f1+50)
def rms_db(x):return 10.0*math.log10(max(np.mean(x**2),1e-12))
demos=parse(PLAN)
for label in ["hello","annyeong","yeobo"]:
    d=demos[label];x=load(FILES[label])
    print("== %s len=%d pred=%d"%(label,len(x),d["outlen"]))
    spans=out_spans(d)
    for b in d["bounds"]:
        k={"hello":{1:0,2:1,3:2},"annyeong":{n:n-1 for n in range(1,12)},"yeobo":{n:n-1 for n in range(1,8)}}[label][b["b"]]
        pl="+".join(LABELS[label][u] for u in d["work"][k]);nl="+".join(LABELS[label][u] for u in d["work"][k+1])
        fric=any(LABELS[label][u] in FRIC for u in d["work"][k]) or any(LABELS[label][u] in FRIC for u in d["work"][k+1])
        z0,z1=b["z0"],b["z1"]
        f2pre=frame_f2(x,z0-FWIN);f2post=frame_f2(x,z1)
        s0,s1=spans[k];t0,t1=spans[k+1]
        rstep=rms_db(x[t0+EDGE:t1-EDGE])-rms_db(x[s0+EDGE:s1-EDGE])
        print("b%d %s->%s nose %.0f/%.0f d=%.0f rms %+.2f%s"%(b["b"],pl,nl,f2pre,f2post,abs(f2post-f2pre),rstep," FRIC" if fric else ""))
