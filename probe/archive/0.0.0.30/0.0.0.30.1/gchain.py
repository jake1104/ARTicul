"""0.0.0.30.1 shared chain replica: plan parsing, work geometry, exact float64
ports of level_output (cap+12dB, prescale 1.10x, causal follower) and
coherence_rms_normalize (mean-target +-6dB, peakcap 0.9, 0.989 rescale,
single-sample de-click), full-chain fixed-point inversion, gate metrics.
Mirrors crates/articul-cli/src/synth.rs (current tree, 0.0.0.29.2 residue).
"""
import re, os
import numpy as np

ROOT = r"E:\01_coding\ARTicul"
P = os.path.join(ROOT, "probe", "0.0.0.30.1")
SR = 22050

WIN = SR // 50          # 441
MTAM = int(SR * 0.005)  # 110 (truncation, matches `as usize`)
ATK = np.exp(-(WIN / SR) / 0.012)
REL = np.exp(-(WIN / SR) / 0.008)
GC = np.exp(-(WIN / SR) / 0.010)
GLIDE = int(0.050 * SR)   # 1102 (truncation)
SHORT = int(0.008 * SR)   # 176
EDGE = int(0.010 * SR)    # 220


def _norm_sym(s):
    if s.startswith("\\u") and len(s) == 6:
        try:
            return chr(int(s[2:], 16))
        except ValueError:
            return s
    return s


def load_plan():
    items, cur = {}, None
    pat = re.compile(r"u(\d+) sym=(.*?) dur=(\d+)ms stress=(\S+) word_final=(\S+) pause=(\S+) seglen=(\d+) arm=(\S+) base=(\S+) decl=(\S+) fin=(\S+) floor=(\d+) engine=(\S+)dB match=(\S+)")
    for line in open(os.path.join(P, "plan.txt"), encoding="utf8"):
        line = line.rstrip("\n")
        m = re.match(r"== (.+?) :: (.*)", line)
        if m:
            cur = m.group(1)
            items[cur] = {"text": m.group(2), "segs": []}
            continue
        m = pat.match(line)
        if m and cur is not None:
            items[cur]["segs"].append({
                "i": int(m.group(1)), "sym": _norm_sym(m.group(2)),
                "dur": int(m.group(3)), "stress": m.group(4),
                "word_final": m.group(5) == "True", "pause": m.group(6) == "True",
                "seglen": int(m.group(7)), "arm": m.group(8),
                "base": float(m.group(9)), "decl": float(m.group(10)),
                "fin": float(m.group(11)), "floor": int(m.group(12)),
                "g": float(m.group(13)),
            })
    return items


VOWEL_ARMS = ("stressed-vowel", "unstressed-vowel")


def _is_goat_pair(a, b):
    return (a["sym"] == "o" and a["stress"] != "Unstressed"
            and a["arm"] in VOWEL_ARMS and b["sym"] == "\u028a"
            and b["stress"] == "Unstressed" and b["arm"] in VOWEL_ARMS)


def work_geometry(segs):
    """Mirror render_units work groups + fades. Returns dict with groups,
    lens, starts, fades (all sample geometry), seg_ranges [(s0,s1)] per seg."""
    groups, i = [], 0
    while i < len(segs):
        if i + 1 < len(segs) and _is_goat_pair(segs[i], segs[i + 1]):
            groups.append([i, i + 1]); i += 2
        else:
            groups.append([i]); i += 1
    lens = [sum(segs[j]["seglen"] for j in g) for g in groups]
    fades = [0] * len(groups)
    for gi in range(1, len(groups)):
        la = segs[groups[gi - 1][-1]]["arm"] in VOWEL_ARMS
        rb = segs[groups[gi][0]]["arm"] in VOWEL_ARMS
        fades[gi] = GLIDE if (la and rb) else SHORT
    starts = [0]
    for gi in range(1, len(groups)):
        pos = starts[gi - 1] + lens[gi - 1]
        pos -= min(fades[gi], pos)
        starts.append(pos)
    seg_ranges = []
    for gi, g in enumerate(groups):
        base = starts[gi] + (fades[gi] if gi > 0 else 0)
        if len(g) == 2:
            l0 = segs[g[0]]["seglen"]
            seg_ranges.append((base, base + l0))
            seg_ranges.append((base + l0, starts[gi] + lens[gi]))
        else:
            seg_ranges.append((base, starts[gi] + lens[gi]))
    return {"groups": groups, "lens": lens, "starts": starts, "fades": fades,
            "seg_ranges": seg_ranges}


def forward_leveler(pre, cap_db=12.0, prescale=1.10):
    x = np.array(pre, dtype=np.float64).copy()
    p0 = max(float(np.max(np.abs(x))), 1e-9)
    a2 = x * x
    cs = np.concatenate([[0.0], np.cumsum(a2)])
    idx = np.arange(len(x))
    lo = np.maximum(0, idx + 1 - MTAM)
    rsum = cs[idx + 1] - cs[lo]
    rc = np.minimum(idx + 1, MTAM)
    r = np.sqrt(rsum / rc)
    t = np.maximum(2.2 * r, 0.05 * p0)
    av = np.abs(x)
    over = av > t
    x[over] *= (t[over] + (av[over] - t[over]) * 0.08) / av[over]
    n = len(x); nw = (n + WIN - 1) // WIN
    wr = np.zeros(nw)
    for i in range(nw):
        s = x[i * WIN:min((i + 1) * WIN, n)]
        wr[i] = np.sqrt((s * s).mean())
    pk = max(float(wr.max()), 1e-9)
    env = np.zeros(nw)
    e = max(wr[0], pk / 1000.0)
    for i in range(nw):
        tgt = max(wr[i], pk / 1000.0)
        c = ATK if tgt > e else REL
        e = c * e + (1 - c) * tgt
        env[i] = e
    edb = 20 * np.log10(np.maximum(env, 1e-12) / pk)
    gdb = np.where(edb >= -12.0, -0.20 * edb, 2.4 - 0.85 * (edb + 12.0))
    gdb = np.where(edb > -3.0, gdb - (edb + 3.0) * 0.5, gdb)
    gdb = np.minimum(gdb, cap_db)
    g = 10.0 ** (gdb / 20.0)
    prev = 1.0
    for i in range(nw):
        prev = GC * prev + (1 - GC) * g[i]
        g[i] = prev
    pos = np.arange(n) / float(WIN)
    k = np.minimum(pos.astype(int), nw - 1)
    frac = np.clip(pos - k, 0, 1)
    k1 = np.minimum(k + 1, nw - 1)
    gi = g[k] + (g[k1] - g[k]) * frac
    x = x * gi
    maxv = max(float(np.max(np.abs(x))), 1e-9)
    G = prescale * 0.989 / maxv
    y = np.clip(x * G, -0.989, 0.989)
    return y, g, G, gdb


def forward_coherence(x, segs, geom, coh_cap=6.0):
    x = np.array(x, dtype=np.float64).copy()
    groups, lens, starts, fades = (geom["groups"], geom["lens"],
                                   geom["starts"], geom["fades"])
    nw = len(groups)
    if nw == 0 or len(x) == 0:
        return x, np.ones(1), {}
    rms_per = np.zeros(nw); peak_per = np.zeros(nw)
    vals = []
    for idx, g in enumerate(groups):
        s0 = starts[idx]; s1 = min(starts[idx] + lens[idx], len(x))
        if s1 - s0 <= 2 * EDGE:
            continue
        lo = min(s0 + EDGE, len(x)); hi = max(s1 - EDGE, lo)
        seg = x[lo:min(hi, len(x))]
        if len(seg) == 0:
            continue
        r = float(np.sqrt((seg * seg).mean()))
        rms_per[idx] = r
        peak_per[idx] = float(np.max(np.abs(seg)))
        u = segs[g[0]]
        if not u["pause"] and u["stress"] != "Primary" and r > 1e-12:
            vals.append(r)
    if len(vals) == 0:
        return x, np.ones(nw), {"idle": True}
    target = max(float(np.sum(vals) / len(vals)), 1e-12)
    gains = np.ones(nw)
    for idx, g in enumerate(groups):
        u = segs[g[0]]
        if u["pause"] or u["stress"] == "Primary":
            gains[idx] = 1.0
        else:
            r = max(rms_per[idx], 1e-12); p = max(peak_per[idx], 1e-9)
            gdb = 20 * np.log10(min(target / r, 0.9 / p))
            gdb = max(-coh_cap, min(coh_cap, gdb))
            gains[idx] = 10.0 ** (gdb / 20.0)
    track = np.ones(len(x))
    for idx in range(nw):
        es = 0 if idx == 0 else min(starts[idx] + min(fades[idx], lens[idx]), len(x))
        ee = min(starts[idx + 1], len(x)) if idx + 1 < nw else len(x)
        if es < ee:
            track[es:ee] = gains[idx]
        if idx > 0:
            b0 = min(starts[idx], len(x)); b1 = min(starts[idx] + fades[idx], len(x))
            n = b1 - b0
            if n > 0:
                u = np.arange(n) / max(n, 1)
                track[b0:b1] = gains[idx - 1] + (gains[idx] - gains[idx - 1]) * u
    x = x * track
    maxv = max(float(np.max(np.abs(x))), 1e-9)
    Gc = 0.989 / maxv
    x = x * Gc
    for s in starts[1:]:
        if 0 < s < len(x) - 1:
            x[s] = 0.5 * (x[s - 1] + x[s + 1])
    x = np.clip(x, -0.989, 0.989)
    return x, gains, {"idle": False, "target": target, "Gc": Gc}


def forward_full(pre, segs, geom, cap_db=12.0, prescale=1.10, coherence=True,
                 coh_cap=6.0):
    y, g, G, gdb = forward_leveler(pre, cap_db, prescale)
    info = {"g": g, "G": G, "gdb": gdb}
    if coherence:
        y, cg, cinfo = forward_coherence(y, segs, geom, coh_cap)
        info.update({"cgains": cg, "cinfo": cinfo})
    return y, info


def invert_full(y, segs, geom, iters=150, cap_db=12.0, prescale=1.10,
                coherence=True):
    y = np.array(y, dtype=np.float64).copy()
    pre = y.copy()
    for _ in range(iters):
        f, _ = forward_full(pre, segs, geom, cap_db, prescale, coherence)
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = np.where(np.abs(f) > 1e-9, y / f, 1.0)
        ratio = np.clip(ratio, 0.25, 4.0)
        # Freeze where either side clips: the true-clipped peak (|y|>=0.985)
        # is unrecoverable, and the forward Gc re-pins its max every pass, so
        # updating a forward-clipped sample only feeds the runaway.
        # Max-anchor keeps the scale at the nearby fixed point (scale family).
        frozen = (np.abs(f) >= 0.985) | (np.abs(y) >= 0.985)
        ratio[frozen] = 1.0
        pre = pre * ratio
        anchor = max(float(np.max(np.abs(y))), 1e-9) / max(float(np.max(np.abs(pre))), 1e-12)
        pre = pre * anchor
    f, info = forward_full(pre, segs, geom, cap_db, prescale, coherence)
    uncl = (np.abs(y) < 0.985) & (np.abs(f) < 0.985)
    resid = float(np.max(np.abs(f[uncl] - y[uncl]))) if uncl.any() else 0.0
    return pre, info, resid


# ---------- gate-metric mirrors ----------
def rms(v):
    return float(np.sqrt((np.asarray(v) * np.asarray(v)).mean())) if len(v) else 0.0


def trough_max_db(x):
    wlen = SR // 100
    nw = len(x) // wlen
    if nw < 26:
        return 0.0
    nrms = np.sqrt((np.asarray(x[:nw * wlen]).reshape(nw, wlen) ** 2).mean(axis=1))
    worst = 0.0
    for k in range(10, nw - 15):
        ctx = float(nrms[k - 10:k].mean())
        if ctx <= 1e-9 or nrms[k] <= 1e-9:
            continue
        worst = min(worst, 20.0 * np.log10(float(nrms[k]) / ctx))
    return worst


def spark_windows(x, geom):
    win = round(10 / 1000 * SR)
    out = []
    for gi in range(1, len(geom["groups"])):
        s0 = min(geom["starts"][gi], len(x) - 1)
        seg = np.asarray(x[s0:s0 + win])
        a = np.abs(seg)
        cl = int((a >= 0.985).sum())
        pk = float(a[a < 0.985].max()) if (a < 0.985).any() else 0.0
        out.append((gi, s0, pk, cl))
    return out
