"""0.0.0.28.1 part 3: HALF-table proposal simulation on recovered pre-leveler
signals through a parametrized leveler replica (cap_db, prescale).
Grid-searches leveler targets; predicts spark/gate metrics. Read-only."""
import re, wave, os
import numpy as np

ROOT = r"E:\01_coding\ARTicul"
P = os.path.join(ROOT, "probe", "0.0.0.28.1")
SR = 22050
WIN = SR // 50
M = round(SR * 0.005)
ATK = np.exp(-(WIN/SR) / 0.012)
REL = np.exp(-(WIN/SR) / 0.008)
GC = np.exp(-(WIN/SR) / 0.010)

items, cur = {}, None
for line in open(os.path.join(P, "plan.txt"), encoding="utf8"):
    line = line.rstrip("\n")
    m = re.match(r"== (.+?) :: (.*)", line)
    if m:
        cur = m.group(1); items[cur] = {"text": m.group(2), "segs": []}
        continue
    m = re.match(r"u(\d+) sym=(.*?) dur=(\d+)ms stress=(\S+) word_final=(\S+) pause=(\S+) seglen=(\d+) arm=(\S+) base=(\S+) decl=(\S+) fin=(\S+) floor=(\d+) engine=(\S+)dB match=(\S+)", line)
    if m and cur is not None:
        items[cur]["segs"].append({
            "i": int(m.group(1)), "sym": m.group(2), "arm": m.group(8),
            "base": float(m.group(9)), "decl": float(m.group(10)),
            "fin": float(m.group(11)), "g": float(m.group(13)), "seglen": int(m.group(7)),
        })

VOWEL_ARMS = ("stressed-vowel", "unstressed-vowel")

def work_groups(segs):
    groups, i = [], 0
    while i < len(segs):
        if (i + 1 < len(segs) and segs[i]["arm"] == "stressed-vowel"
                and segs[i]["sym"] == "o" and segs[i+1]["arm"] == "unstressed-vowel"):
            groups.append([i, i+1]); i += 2
        else:
            groups.append([i]); i += 1
    return groups

def forward(pre, cap_db=16.0, prescale=1.25):
    x = pre.copy()
    p0 = max(float(np.max(np.abs(x))), 1e-9)
    a2 = x*x
    cs = np.concatenate([[0.0], np.cumsum(a2)])
    idx = np.arange(len(x))
    lo = np.maximum(0, idx - M + 1)
    rsum = cs[idx+1] - cs[lo]
    rc = np.minimum(idx + 1, M)
    r = np.sqrt(rsum / rc)
    t = np.maximum(2.2*r, 0.05*p0)
    av = np.abs(x)
    over = av > t
    x[over] *= (t[over] + (av[over]-t[over])*0.08) / av[over]
    n = len(x); nw = (n + WIN - 1)//WIN
    wr = np.zeros(nw)
    for i in range(nw):
        s = x[i*WIN:min((i+1)*WIN, n)]
        wr[i] = np.sqrt((s*s).mean())
    pk = max(float(wr.max()), 1e-9)
    env = np.zeros(nw)
    e = max(wr[0], pk/1000.0)
    for i in range(nw):
        tgt = max(wr[i], pk/1000.0)
        c = ATK if tgt > e else REL
        e = c*e + (1-c)*tgt
        env[i] = e
    edb = 20*np.log10(np.maximum(env, 1e-12)/pk)
    gdb = np.where(edb >= -12.0, -0.20*edb, 2.4 - 0.85*(edb+12.0))
    gdb = np.where(edb > -3.0, gdb - (edb+3.0)*0.5, gdb)
    gdb = np.minimum(gdb, cap_db)
    g = 10.0**(gdb/20.0)
    prev = 1.0
    for i in range(nw):
        prev = GC*prev + (1-GC)*g[i]
        g[i] = prev
    pos = np.arange(n)/float(WIN)
    k = np.minimum(pos.astype(int), nw-1)
    frac = np.clip(pos - k, 0, 1)
    k1 = np.minimum(k+1, nw-1)
    gi = g[k] + (g[k1]-g[k])*frac
    x = x*gi
    maxv = max(float(np.max(np.abs(x))), 1e-9)
    G = prescale*0.989/maxv
    y = np.clip(x*G, -0.989, 0.989)
    return y, g, G, gdb

def load(name):
    w = wave.open(os.path.join(P, name + ".wav"), "rb")
    n = w.getnframes()
    x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float64) / 32768.0
    return n, x

def invert(y, iters=60):
    pre = y.copy()
    for _ in range(iters):
        f, _, _, _ = forward(pre)
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.where(np.abs(f) > 1e-9, y/f, 1.0)
        pre = pre*np.clip(ratio, 0.25, 4.0)
    return pre

def rms(v):
    return float(np.sqrt((v*v).mean())) if len(v) else 0.0

def trough(x):
    wlen = SR//100; nw2 = len(x)//wlen
    nr = np.sqrt((x[:nw2*wlen].reshape(nw2, wlen)**2).mean(axis=1))
    worst = 0.0
    for k in range(10, nw2-15):
        ctx = float(nr[k-10:k].mean())
        if ctx <= 1e-9 or nr[k] <= 1e-9:
            continue
        worst = min(worst, 20.0*np.log10(float(nr[k])/ctx))
    return worst

def spark_report(y, itemname):
    segs = items[itemname]["segs"]
    groups = work_groups(segs)
    lens = [sum(segs[j]["seglen"] for j in g) for g in groups]
    pos = 0; worst = 0.0; det = []
    for gi in range(1, len(groups)):
        a = groups[gi-1][-1]; b = groups[gi][0]
        vv = segs[a]["arm"] in VOWEL_ARMS and segs[b]["arm"] in VOWEL_ARMS
        fade = 1102 if vv else 176
        pos = pos + lens[gi-1]
        pos -= min(fade, pos)
        win = round(10/1000*SR)
        seg = y[pos:pos+win]
        uncl = seg[np.abs(seg) < 0.985]
        pk = float(np.max(np.abs(uncl))) if len(uncl) else 0.0
        nc = int((np.abs(seg) >= 0.985).sum())
        worst = max(worst, pk)
        det.append((gi, pos, pk, nc))
    return worst, det

# proposal deltas per segment
PROP = {}
for name, it in items.items():
    ds = []
    for s in it["segs"]:
        new_raw = s["base"]/2.0 + s["decl"]/2.0 + s["fin"]/2.0
        new = max(new_raw, -6.0)
        ds.append(new - s["g"])
    PROP[name] = ds

print("=== PROPOSAL DELTAS (new-old dB per segment) ===")
for name, ds in PROP.items():
    print("%s: %s" % (name, " ".join("%+.2f" % v for v in ds)))

def delta_track(n, itemname):
    segs = items[itemname]["segs"]
    ds = PROP[itemname]
    groups = work_groups(segs)
    lens = [sum(segs[j]["seglen"] for j in g) for g in groups]
    starts = [0]; pos = 0
    fades = [0]
    for gi in range(1, len(groups)):
        a = groups[gi-1][-1]; b = groups[gi][0]
        vv = segs[a]["arm"] in VOWEL_ARMS and segs[b]["arm"] in VOWEL_ARMS
        fade = 1102 if vv else 176
        pos = pos + lens[gi-1]
        pos -= min(fade, pos)
        starts.append(pos); fades.append(fade)
    # group delta = len-weighted mean of member deltas
    gd = []
    for gi, g in enumerate(groups):
        w = np.array([segs[j]["seglen"] for j in g], float)
        gd.append(float((w*np.array([ds[j] for j in g])).sum()/w.sum()))
    tr = np.zeros(n)
    own = np.zeros(n, dtype=int)
    # ownership: nearest group span
    bounds = starts + [n]
    for gi in range(len(groups)):
        s0 = bounds[gi]; s1 = bounds[gi+1]
        tr[s0:s1] = gd[gi]; own[s0:s1] = gi
    # linear crossfade of ownership across fade zones
    for gi in range(1, len(groups)):
        b = starts[gi]; f = fades[gi]
        s0 = max(0, b-f//2); s1 = min(n, b+f//2)
        if s1 > s0:
            u = (np.arange(s0, s1)-s0)/max(1, s1-s0-1)
            tr[s0:s1] = (1-u)*gd[gi-1] + u*gd[gi]
    # GOAT internal split (sharp, engine-seamless): skip, len-weighted gd already exact-ish
    return tr

DEMOS = ["demo_hello", "annyeong", "yeobo"]
print("=== GRID: cap x prescale on proposal (simulated outputs) ===")
print("gates: rms>=0.10 peak<=0.99 trough>=-14 tail>=0.03 halves|d|<=5 spark_uncl<0.9")
for cap_db in (16.0, 12.0, 10.0, 8.0):
    for prescale in (1.25, 1.1, 1.0):
        line = "cap=%4.1f pre=%4.2f:" % (cap_db, prescale)
        for name in DEMOS:
            n, y = load(name)
            pre = invert(y)
            tr = delta_track(n, name)
            pre2 = pre * 10.0**(tr/20.0)
            y2, g2, G2, gdb2 = forward(pre2, cap_db=cap_db, prescale=prescale)
            pk = float(np.max(np.abs(y2)))
            h0 = rms(y2[:n//2]); h1 = rms(y2[n//2:])
            hd = 20*np.log10(max(h1,1e-9))-20*np.log10(max(h0,1e-9))
            tl = rms(y2[2*(n//3):])
            sp, _ = spark_report(y2, name)
            nc = int((np.abs(y2) >= 0.985).sum())
            ok = (rms(y2) >= 0.10 and pk <= 0.99 and trough(y2) >= -14.0
                  and tl >= 0.03 and abs(hd) <= 5.0 and sp < 0.9)
            line += " %s[rms=%.3f tr=%.1f tail=%.3f halves=%+.1f spark=%.3f cl=%d maxgdb=%.1f %s]" % (
                name.split("_")[-1][:5], rms(y2), trough(y2), tl, hd, sp, nc,
                gdb2.max(), "PASS" if ok else "fail")
        print(line)
