"""0.0.0.28.1 gain-architecture probe analysis (read-only; no engine edits).

Reads plan.txt (engine segment_gain_db via plandump) and fresh renders,
mirrors gate metrics (leveling.rs / balance.rs / demo_measure.py),
ports level_output exactly (causal-only follower, synth.rs:1040-1124),
and recovers the pre-leveler signal by per-sample fixed-point inversion
(validated by forward residual). Reports makeup-gain distribution,
clamp engagement, spark-window peaks, and the dynamic-range split.
"""
import re, wave, hashlib, os
import numpy as np

ROOT = r"E:\01_coding\ARTicul"
P = os.path.join(ROOT, "probe", "0.0.0.28.1")
SR = 22050

# ---------- part 1: planned gains ----------
items, cur = {}, None
for line in open(os.path.join(P, "plan.txt"), encoding="utf8"):
    line = line.rstrip("\n")
    m = re.match(r"== (.+?) :: (.*)", line)
    if m:
        cur = m.group(1)
        items[cur] = []
        continue
    m = re.match(r"u(\d+) sym=(.*?) dur=(\d+)ms stress=(\S+) word_final=(\S+) pause=(\S+) seglen=(\d+) arm=(\S+) base=(\S+) decl=(\S+) fin=(\S+) floor=(\d+) engine=(\S+)dB match=(\S+)", line)
    if m and cur is not None:
        items[cur].append({
            "i": int(m.group(1)), "sym": m.group(2), "dur": int(m.group(3)),
            "stress": m.group(4), "arm": m.group(8), "base": float(m.group(9)),
            "decl": float(m.group(10)), "fin": float(m.group(11)),
            "floor": int(m.group(12)), "g": float(m.group(13)),
        })

print("=== PLANNED GAINS ===")
allg, floorn, near0 = [], 0, 0
arm_min, arm_max, arm_n = {}, {}, {}
for name, segs in items.items():
    gs = [s["g"] for s in segs]
    allg += gs
    floorn += sum(1 for s in segs if s["floor"])
    near0 += sum(1 for s in segs if s["g"] >= -1.0)
    steps = [abs(gs[k+1]-gs[k]) for k in range(len(gs)-1)]
    print("%s n=%d min=%.1f max=%.1f spread=%.1f worst_step=%.1f floor_n=%d" % (
        name, len(gs), min(gs), max(gs), max(gs)-min(gs),
        max(steps) if steps else 0.0, sum(1 for s in segs if s["floor"])))
    for k in range(len(gs)-1):
        sa = segs[k]["sym"].encode("unicode_escape").decode("ascii")
        sb = segs[k+1]["sym"].encode("unicode_escape").decode("ascii")
        print("   step u%d(%s)->u%d(%s): %+.1fdB" % (
            segs[k]["i"], sa, segs[k+1]["i"], sb,
            gs[k+1]-gs[k]))
    for s in segs:
        a = s["arm"]
        arm_min[a] = min(arm_min.get(a, 1e9), s["g"])
        arm_max[a] = max(arm_max.get(a, -1e9), s["g"])
        arm_n[a] = arm_n.get(a, 0) + 1
print("global min=%.1f max=%.1f spread=%.1f total_segs=%d floor_n=%d near0_n=%d" % (
    min(allg), max(allg), max(allg)-min(allg), len(allg), floorn, near0))
print("arm ranges (planned, incl decl/fin/floor):")
for a in sorted(arm_min):
    print("   %-18s n=%2d min=%6.1f max=%5.1f" % (a, arm_n[a], arm_min[a], arm_max[a]))

# unclipped spread (what the table+declination ask for before the floor)
raw_min, raw_max = 1e9, -1e9
for segs in items.values():
    for s in segs:
        raw = s["base"] + s["decl"] + s["fin"]
        raw_min = min(raw_min, raw)
        raw_max = max(raw_max, raw)
print("unclipped planned spread: min=%.1f max=%.1f spread=%.1f (floor hides %.1fdB)" % (
    raw_min, raw_max, raw_max-raw_min, (raw_max-raw_min)-(max(allg)-min(allg))))

# ---------- part 2: wav metrics ----------
def load(name):
    path = os.path.join(P, name + ".wav")
    raw = open(path, "rb").read()
    w = wave.open(path, "rb")
    n = w.getnframes()
    x = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float64) / 32768.0
    return raw, n, x

def rms(v):
    return float(np.sqrt((v*v).mean())) if len(v) else 0.0

def trough_max_db(x):
    wlen = SR // 100
    nw = len(x) // wlen
    nrms = np.sqrt((x[:nw*wlen].reshape(nw, wlen)**2).mean(axis=1))
    worst = 0.0
    for k in range(10, nw-15):
        ctx = float(nrms[k-10:k].mean())
        if ctx <= 1e-9 or nrms[k] <= 1e-9:
            continue
        worst = min(worst, 20.0*np.log10(float(nrms[k])/ctx))
    return worst

NAMES = ["fixed_sentence", "demo_hello", "creak_probe", "gain_probe",
         "cluster_probe", "pause_probe", "annyeong", "yeobo"]
print("=== RENDER METRICS ===")
for name in NAMES:
    raw, n, x = load(name)
    peak = float(np.max(np.abs(x)))
    g = rms(x)
    h0 = rms(x[:n//2]); h1 = rms(x[n//2:])
    nclamp = int((np.abs(x) >= 0.985).sum())
    tail = rms(x[2*(n//3):])
    print("%s samples=%d sha=%.8s peak=%.4f rms=%.4f halves=%+.2fdB trough=%.2fdB tail=%.4f clamp_n=%d" % (
        name, n, hashlib.sha256(raw).hexdigest(), peak, g,
        20*np.log10(max(h1,1e-9))-20*np.log10(max(h0,1e-9)),
        trough_max_db(x), tail, nclamp))

# byte identity vs shipped demos
for a, b in [("demo_hello", "demo/hello.wav"), ("annyeong", "demo/annyeonghaseyo.wav"),
             ("yeobo", "demo/yeoboseyo.wav")]:
    ra = open(os.path.join(P, a + ".wav"), "rb").read()
    rb = open(os.path.join(ROOT, b), "rb").read()
    print("identity %s vs %s: %s (sizes %d/%d)" % (a, b, ra == rb, len(ra), len(rb)))

# ---------- part 3: exact leveler replica + fixed-point inversion ----------
WIN = SR // 50  # 441
M = round(SR * 0.005)  # 110
ATK = np.exp(-(WIN/SR) / 0.012)
REL = np.exp(-(WIN/SR) / 0.008)
GC = np.exp(-(WIN/SR) / 0.010)

def forward(pre):
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
    gdb = np.minimum(gdb, 16.0)
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
    G = 1.25*0.989/maxv
    y = np.clip(x*G, -0.989, 0.989)
    return y, g, G, gdb

def invert(y, iters=60):
    pre = y.copy()
    for _ in range(iters):
        f, _, _, _ = forward(pre)
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.where(np.abs(f) > 1e-9, y/f, 1.0)
        ratio = np.clip(ratio, 0.25, 4.0)
        pre = pre*ratio
    f, g, G, gdb = forward(pre)
    uncl = np.abs(y) < 0.985
    resid = float(np.max(np.abs(f[uncl]-y[uncl]))) if uncl.any() else 0.0
    return pre, g, G, gdb, resid

print("=== MAKEUP ESTIMATION (fixed-point inversion) ===")
print("sanity: constant-1.0 input -> gains should be ~1.0, G=1.23625, no clamp")
ys, gs, Gs, _ = forward(np.ones(4410))
print("   const: maxgain=%.6f G=%.6f clamp=%d" % (gs.max(), Gs, (np.abs(ys) >= 0.985).sum()))
MAK = {}
for name in NAMES:
    _, _, y = load(name)
    pre, g, G, gdb, resid = invert(y)
    iu = np.abs(y) < 0.985
    lift = g * G
    MAK[name] = (g, G, gdb, y, pre)
    print("%s inw=%d G=%.4f (%.2fdB) resid=%.2e" % (name, len(g), G, 20*np.log10(G), resid))
    print("   makeup dB: max=%.2f mean=%.2f p50=%.2f frac_win>=12dB=%.3f frac_win>=16dB(cap)=%.3f" % (
        gdb.max(), gdb.mean(), np.median(gdb),
        (gdb >= 12.0).mean(), (gdb >= 15.99).mean()))
    print("   makeup lin: max=%.2fx mean=%.2fx | total lift max=%.2fx mean=%.2fx frac_lift>=8x=%.3f" % (
        g.max(), g.mean(), lift.max(), lift.mean(), (lift >= 8.0).mean()))
    # trough windows: leveler windows overlapping deepest trough region
    wlen = SR//100
    nw2 = len(y)//wlen
    nr = np.sqrt((y[:nw2*wlen].reshape(nw2, wlen)**2).mean(axis=1))
    k = int(np.argmin(nr[10:nw2-15])) + 10 if nw2 > 25 else int(np.argmin(nr))
    lw = min(int((k*wlen)/WIN), len(g)-1)
    print("   deepest trough ~10ms-win %d (lvl-win %d): makeup=%.2fdB total_lift=%.2fx" % (
        k, lw, gdb[lw], lift[lw]))

np.savez(os.path.join(P, "makeup.npz"),
         **{n: MAK[n][0] for n in NAMES},
         **{n + "_G": np.array([MAK[n][1]]) for n in NAMES})
print("saved makeup.npz")
