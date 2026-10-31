"""0.0.0.28.1 part 5: variant grid on f32 signals. Variants change per-arm
deltas only (proposal table), leveler cap/prescale parametrized. Includes
hello/old-input word-balance mirror + BASE identity check."""
import re, os
import numpy as np

ROOT = r"E:\01_coding\ARTicul"
P = os.path.join(ROOT, "probe", "0.0.0.28.1")
SR = 22050
WIN = SR // 50
M = round(SR * 0.005)
ATK = np.exp(-(WIN/SR) / 0.012)
REL = np.exp(-(WIN/SR) / 0.008)
GC = np.exp(-(WIN/SR) / 0.010)
VOWEL_ARMS = ("stressed-vowel", "unstressed-vowel")

items, cur = {}, None
for line in open(os.path.join(P, "plan.txt"), encoding="utf8"):
    line = line.rstrip("\n")
    m = re.match(r"== (.+?) :: (.*)", line)
    if m:
        cur = m.group(1); items[cur] = {"text": m.group(2), "segs": []}
        continue
    m = re.match(r"u(\d+) sym=(.*?) dur=(\d+)ms stress=(\S+) word_final=(\S+) pause=(\S+) seglen=(\d+) arm=(\S+) base=(\S+) decl=(\S+) fin=(\S+) floor=(\d+) engine=(\S+)dB match=(\S+)", line)
    if m and cur is not None:
        items[cur]["segs"].append({"i": int(m.group(1)), "sym": m.group(2),
            "arm": m.group(8), "base": float(m.group(9)), "decl": float(m.group(10)),
            "fin": float(m.group(11)), "g": float(m.group(13)), "seglen": int(m.group(7))})

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
    av = np.abs(x); over = av > t
    x[over] *= (t[over] + (av[over]-t[over])*0.08) / av[over]
    n = len(x); nw = (n + WIN - 1)//WIN
    wr = np.array([np.sqrt(((x[i*WIN:min((i+1)*WIN, n)])**2).mean()) for i in range(nw)])
    pk = max(float(wr.max()), 1e-9)
    env = np.zeros(nw); e = max(wr[0], pk/1000.0)
    for i in range(nw):
        tgt = max(wr[i], pk/1000.0)
        c = ATK if tgt > e else REL
        e = c*e + (1-c)*tgt; env[i] = e
    edb = 20*np.log10(np.maximum(env, 1e-12)/pk)
    gdb = np.where(edb >= -12.0, -0.20*edb, 2.4 - 0.85*(edb+12.0))
    gdb = np.where(edb > -3.0, gdb - (edb+3.0)*0.5, gdb)
    gdb = np.minimum(gdb, cap_db)
    g = 10.0**(gdb/20.0)
    prev = 1.0
    for i in range(nw):
        prev = GC*prev + (1-GC)*g[i]; g[i] = prev
    pos = np.arange(n)/float(WIN)
    k = np.minimum(pos.astype(int), nw-1)
    frac = np.clip(pos - k, 0, 1)
    k1 = np.minimum(k+1, nw-1)
    x = x*(g[k] + (g[k1]-g[k])*frac)
    maxv = max(float(np.max(np.abs(x))), 1e-9)
    G = prescale*0.989/maxv
    return np.clip(x*G, -0.989, 0.989), g, G, gdb

def loadf(name):
    return np.fromfile(os.path.join(P, name + ".f32"), dtype=np.float32).astype(np.float64)

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

def work_groups(segs):
    groups, i = [], 0
    while i < len(segs):
        if (i+1 < len(segs) and segs[i]["arm"] == "stressed-vowel" and segs[i]["sym"] == "o"
                and segs[i+1]["arm"] == "unstressed-vowel"):
            groups.append([i, i+1]); i += 2
        else:
            groups.append([i]); i += 1
    return groups

def spark(y, itemname):
    segs = items[itemname]["segs"]
    groups = work_groups(segs)
    lens = [sum(segs[j]["seglen"] for j in g) for g in groups]
    pos = 0; worst = 0.0
    for gi in range(1, len(groups)):
        a = groups[gi-1][-1]; b = groups[gi][0]
        vv = segs[a]["arm"] in VOWEL_ARMS and segs[b]["arm"] in VOWEL_ARMS
        fade = 1102 if vv else 176
        pos = pos + lens[gi-1]
        pos -= min(fade, pos)
        seg = y[pos:pos+220]
        uncl = seg[np.abs(seg) < 0.985]
        pk = float(np.max(np.abs(uncl))) if len(uncl) else 0.0
        worst = max(worst, pk)
    return worst

def word_bounds(itemname, word_nsegs):
    segs = items[itemname]["segs"]
    vow = [s["arm"] in VOWEL_ARMS for s in segs]
    lens = [s["seglen"] for s in segs]
    bounds = []; pos = 0; wstart = 0; idx = 0
    for wi, nw in enumerate(word_nsegs):
        for k in range(nw):
            if k > 0:
                fade = 1102 if (vow[idx-1] and vow[idx]) else 176
                pos -= min(fade, pos)
            elif wi > 0:
                fade = 1102 if (vow[idx-1] and vow[idx]) else 176
                pos -= min(fade, pos)
            pos += lens[idx]; idx += 1
        bounds.append((wstart, pos)); wstart = pos
    return bounds

def word_db(out, s, e):
    s = (s+300); e = max(e-300, s+1)
    e = min(e, len(out))
    v = out[s:e]
    return 20*np.log10(max(rms(v), 1e-9))

# variant delta rules: (new_base rule, decl scale, fin scale, floor)
def make_deltas(keep_h=False, uv_new=None):
    D = {}
    for name, it in items.items():
        ds = []
        for s in it["segs"]:
            b = s["base"]
            if keep_h and s["arm"] == "h-fric":
                nb = b
            elif uv_new is not None and s["arm"] == "unstressed-vowel":
                nb = uv_new
            else:
                nb = b/2.0
            new = max(nb + s["decl"]/2.0 + s["fin"]/2.0, -6.0)
            ds.append(new - s["g"])
        D[name] = ds
    return D

VARIANTS = {
    "BASE": (None, 16.0, 1.25),
    "B_pre10": (None, 16.0, 1.0),
    "V1_half_cap12_pre11": (make_deltas(), 12.0, 1.1),
    "V2_halfkeeph_cap12_pre11": (make_deltas(keep_h=True), 12.0, 1.1),
    "V3_halfkeeph_cap12_pre10": (make_deltas(keep_h=True), 12.0, 1.0),
    "V4_halfkeeph_uv25_cap12_pre11": (make_deltas(keep_h=True, uv_new=-2.5), 12.0, 1.1),
    "V5_halfkeeph_cap10_pre11": (make_deltas(keep_h=True), 10.0, 1.1),
}

def delta_track(n, itemname, D):
    segs = items[itemname]["segs"]
    ds = D[itemname]
    groups = work_groups(segs)
    lens = [sum(segs[j]["seglen"] for j in g) for g in groups]
    starts = [0]; pos = 0; fades = [0]
    for gi in range(1, len(groups)):
        a = groups[gi-1][-1]; b = groups[gi][0]
        vv = segs[a]["arm"] in VOWEL_ARMS and segs[b]["arm"] in VOWEL_ARMS
        fade = 1102 if vv else 176
        pos = pos + lens[gi-1]
        pos -= min(fade, pos)
        starts.append(pos); fades.append(fade)
    gd = []
    for g in groups:
        w = np.array([segs[j]["seglen"] for j in g], float)
        gd.append(float((w*np.array([ds[j] for j in g])).sum()/w.sum()))
    tr = np.zeros(n)
    bounds = starts + [n]
    for gi in range(len(groups)):
        tr[bounds[gi]:bounds[gi+1]] = gd[gi]
    for gi in range(1, len(groups)):
        b = starts[gi]; f = fades[gi]
        s0 = max(0, b-f//2); s1 = min(n, b+f//2)
        if s1 > s0:
            u = (np.arange(s0, s1)-s0)/max(1, s1-s0-1)
            tr[s0:s1] = (1-u)*gd[gi-1] + u*gd[gi]
    return tr

DEMOS = ["demo_hello", "annyeong", "yeobo"]
ALL = ["fixed_sentence", "demo_hello", "creak_probe", "gain_probe", "cluster_probe",
       "pause_probe", "annyeong", "yeobo", "old_input"]
PRE = {n: invert(loadf(n)) for n in ALL}
Y0 = {n: loadf(n) for n in ALL}
print("inversion check done")

for vname, (D, cap_db, prescale) in VARIANTS.items():
    print("=== %s cap=%.1f pre=%.2f ===" % (vname, cap_db, prescale))
    for name in ALL:
        y = Y0[name]
        if D is None:
            y2, g2, G2, gdb2 = forward(PRE[name], cap_db, prescale)
        else:
            pre2 = PRE[name]*10.0**(delta_track(len(y), name, D)/20.0)
            y2, g2, G2, gdb2 = forward(pre2, cap_db, prescale)
        n = len(y2)
        pk = float(np.max(np.abs(y2)))
        h0 = rms(y2[:n//2]); h1 = rms(y2[n//2:])
        hd = 20*np.log10(max(h1,1e-9))-20*np.log10(max(h0,1e-9))
        tl = rms(y2[2*(n//3):])
        tr = trough(y2)
        nc = int((np.abs(y2) >= 0.985).sum())
        sp = spark(y2, name) if name in DEMOS else float("nan")
        extra = ""
        if name == "demo_hello":
            b = word_bounds(name, [2, 3])
            bal = word_db(y2, *b[1]) - word_db(y2, *b[0])
            extra = " bal=%+.2f" % bal
        if name == "old_input":
            b = word_bounds(name, [2, 3])
            bal = word_db(y2, *b[1]) - word_db(y2, *b[0])
            extra = " viol=%+.2f(%s)" % (bal, "PIN" if bal < -6.0 else "LOST")
        print("  %-14s rms=%.4f pk=%.4f halves=%+.2f trough=%+.2f tail=%.4f spark=%.4f cl=%d maxgdb=%.1f meangdb=%.1f%s" % (
            name, rms(y2), pk, hd, tr, tl, sp, nc, gdb2.max(), gdb2.mean(), extra))
