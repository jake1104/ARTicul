"""0.0.0.34.1 probe: exact Python replica of plan_utterance durations + f0_track.
Read-only replica of crates/articul-front/src/prosody.rs + xsampa stress rule
+ vowels.rs targets. Validated against probe/archive/0.0.0.24/0.0.0.24.1/plan.txt
(old inputs); then applied to current shipped inputs.
"""
import json, math

M64 = 0xFFFFFFFFFFFFFFFF
SALT = 0x9E3779B97F4A7C15

def splitmix64(x):
    x = (x + 0x9E3779B97F4A7C15) & M64
    z = x
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & M64
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & M64
    return (z ^ (z >> 31)) & M64

def duration_variance(i):
    r = splitmix64((i ^ SALT) & M64) / float(0x10000000000000000)
    return 1.0 + 0.12 * (r - 0.5)

# phoneme features: (is_vowel, intrinsic_ms, sonorant, vl_obstruent, place, F1,F2,F3 or None)
FEAT = {
    'a':  (True, 180.0, True, False, None, (730.0, 1250.0, 2640.0)),
    'V':  (True, 155.0, True, False, None, (600.0, 1150.0, 2270.0)),
    'e':  (True, 160.0, True, False, None, (480.0, 1950.0, 2700.0)),
    'o':  (True, 160.0, True, False, None, (480.0, 950.0, 2300.0)),
    '@':  (True, 110.0, True, False, None, (520.0, 1500.0, 2440.0)),
    'E':  (True, 155.0, True, False, None, (600.0, 1720.0, 2420.0)),
    'U':  (True, 125.0, True, False, None, (400.0, 1000.0, 2360.0)),
    'n':  (False, 90.0, True, False, 'alveolar', None),
    'N':  (False, 90.0, True, False, 'velar', None),
    'j':  (False, 90.0, True, False, 'palatal', None),
    'l':  (False, 90.0, True, False, 'alveolar', None),
    'h':  (False, 130.0, False, True, 'glottal', None),
    'h\\':(False, 110.0, False, False, 'glottal', None),
    's':  (False, 130.0, False, True, 'alveolar', None),
    'b':  (False, 90.0, False, False, 'bilabial', None),
}

def transcribe(word):
    """(symbols, stress) mirroring Xsampa::transcribe stress rule."""
    table = ['h\\', 'a', 'V', 'e', 'o', '@', 'E', 'U', 'n', 'N', 'j', 'l', 'h', 's', 'b']
    syms, stress = [], []
    pending = 'U'
    i = 0
    while i < len(word):
        c = word[i]
        if c == '"':
            pending = 'P'; i += 1; continue
        if c == '%':
            pending = 'S'; i += 1; continue
        hit = None
        for L in (2, 1):
            s = word[i:i+L]
            if s in table:
                hit = s; break
        if hit is None:
            i += 1; continue
        i += len(hit)
        syms.append(hit)
        is_v = FEAT[hit][0]
        if is_v:
            stress.append(pending); pending = 'U'
        else:
            stress.append('U')
    return syms, stress

def phrase_st(pos):
    if pos < 0.2:
        return 2.0
    e = math.exp(-2.0 * (pos - 0.2))
    e_end = math.exp(-1.6)
    return -1.0 + 3.0 * (e - e_end) / (1.0 - e_end)

def st_ratio(st):
    return 2.0 ** (st / 12.0)

def plan_text(text, rate=1.0, pitch_scale=1.0, base_f0=120.0):
    words = text.split()
    seq, fst = [], []
    bounds = []
    for w in words:
        syms, st = transcribe(w)
        b = 0.0
        for c in w:
            s = {'!': 1.0, '.': 1.0, '|': 0.6, ';': 0.5, ':': 0.5, ',': 0.4}.get(c, 0.0)
            b = max(b, s)
        bounds.append(b)
        for k, s in enumerate(syms):
            seq.append(s); fst.append(st[k])
    n = len(seq)
    if bounds:
        bounds[-1] = max(bounds[-1], 1.0)
    starts = [0]
    seg = 0
    for wi in range(len(words)):
        if wi > 0 and bounds[wi-1] >= 0.5:
            starts.append(seg)
        seg += len(transcribe(words[wi])[0])
    # nucleus
    last_p = last_s = last_v = None
    for i, s in enumerate(seq):
        if FEAT[s][0]:
            last_v = i
            if fst[i] == 'P': last_p = i
            elif fst[i] == 'S': last_s = i
    nucleus = last_p if last_p is not None else (last_s if last_s is not None else last_v)
    # accents
    accents = []
    if nucleus is not None:
        prior = 0
        for i, s in enumerate(seq):
            if i > nucleus: break
            if FEAT[s][0]:
                if i == nucleus:
                    accents.append((i, 5.0))
                elif fst[i] == 'P':
                    accents.append((i, 3.0 - 1.5 * prior)); prior += 1
                elif fst[i] == 'S':
                    accents.append((i, 1.5 - 1.5 * prior)); prior += 1
    def phrase_pos(i):
        start = 0
        for st in starts:
            if st <= i: start = st
        end = n
        for st in starts:
            if st > i and st < end: end = st
        span = max(end - (start + 1), 1)
        return (i - start) / span
    track = []
    for i in range(n):
        pos = phrase_pos(i)
        if nucleus is None:
            st = -7.0 if (n > 1 and i + 1 == n) else phrase_st(pos)
        else:
            if i == nucleus:
                st = phrase_st(pos) + 5.0
            elif n > 1 and i + 1 == n:
                st = -7.0
            else:
                tail = 0.0
                for (aidx, aamp) in accents:
                    if aidx == i + 1:
                        tail += 0.3 * aamp
                    elif aidx <= i:
                        tail += aamp * (0.5 ** (i - aidx))
                st = phrase_st(pos) + tail
        track.append(base_f0 * pitch_scale * st_ratio(st))
    # durations
    nsyl = []
    lastv = []
    for w in words:
        syms, _ = transcribe(w)
        c = sum(1 for s in syms if FEAT[s][0])
        lv = max([k for k, s in enumerate(syms) if FEAT[s][0]], default=None)
        nsyl.append(c); lastv.append(lv)
    out = []
    fi = 0
    for wi, w in enumerate(words):
        syms, _ = transcribe(w)
        for k, s in enumerate(syms):
            is_v, base, sono, _, _, _ = FEAT[s]
            sf = 1.0 if fst[fi] in ('P', 'S') else 0.55
            ctx = 1.0
            if sono and fi + 1 < n and FEAT[seq[fi+1]][3]:
                ctx = 0.78
            capped = max(sf * ctx, 0.5)
            poly = 1.0 if nsyl[wi] <= 1 else (0.9 if nsyl[wi] == 2 else 0.8)
            func = 1.0
            clu = 0.8 if (not is_v and fi > 0 and not FEAT[seq[fi-1]][0]) else 1.0
            ini = 1.1 if (k == 0 and not is_v) else 1.0
            tier = 1.3 if bounds[wi] >= 1.0 else (1.15 if bounds[wi] >= 0.4 else 1.0)
            fin = tier if (bounds[wi] > 0.0 and lastv[wi] is not None and k >= lastv[wi]) else 1.0
            mindur = 40.0 if is_v else (50.0 if s in ('s', 'h', 'h\\') else 30.0)
            dur = max(round(base * capped * poly * func * clu * fin * ini
                             * duration_variance(fi) / (max(rate, 0.1) ** 0.85)), mindur)
            if s == 'l' and not (k + 1 == len(syms)):
                nxt = seq[fi + 1] if fi + 1 < n else None
                if nxt is not None and FEAT[nxt][0] and fst[fi + 1] in ('P', 'S'):
                    dur = max(dur, 70)
            out.append({'sym': s, 'dur': int(dur), 'f0': track[fi],
                        'f0_end': track[fi+1] if fi + 1 < n else track[fi],
                        'stress': fst[fi]})
            fi += 1
    return out

def reduced(sym, stressed):
    f1, f2, f3 = FEAT[sym][5]
    if stressed:
        return (f1, f2, f3)
    return (f1 + 0.3 * (520.0 - f1), f2 + 0.3 * (1400.0 - f2), f3)

def locus(f1, f2, f3, place):
    if place == 'bilabial':
        return (f1, 0.7 * f2 + 300.0, f3)
    if place == 'alveolar':
        return (f1, 0.3 * f2 + 1100.0, f3)
    if place == 'velar':
        return (f1, 0.5 * f2 + 1200.0, f3 + 0.3 * (2600.0 - f3))
    return (f1, f2, f3)

if __name__ == '__main__':
    # VALIDATION vs archived plan.txt (old inputs)
    import re
    plan = {}
    cur = None
    for line in open('probe/archive/0.0.0.24/0.0.0.24.1/plan.txt', encoding='utf-8'):
        m = re.match(r'== (\w+)', line)
        if m:
            cur = m.group(1); plan[cur] = []
        m = re.match(r'u(\d+) sym=(\S+) dur=(\d+)ms f0=([\d.]+)->([\d.]+)Hz stress=(\w+)', line)
        if m and cur:
            plan[cur].append((m.group(2), int(m.group(3)), float(m.group(4)),
                              float(m.group(5)), m.group(6)))
    SYM = {'ɛ': 'E', 'ʌ': 'V', 'ə': '@', 'ʊ': 'U', 'ŋ': 'N', 'ɦ': 'h\\'}
    SMAP = {'Unstressed': 'U', 'Primary': 'P', 'Secondary': 'S'}
    cases = {'hello': 'hE "loU', 'annyeong': '%an njVN "hasejo', 'yeobo': '%jV"bo%se%jo'}
    ok = True
    for label, text in cases.items():
        mine = plan_text(text)
        ref = plan[label]
        assert len(mine) == len(ref), (label, len(mine), len(ref))
        for u, r in zip(mine, ref):
            rsym = SYM.get(r[0], r[0])
            match = (u['sym'] == rsym and u['dur'] == r[1]
                     and abs(u['f0'] - r[2]) < 0.02 and abs(u['f0_end'] - r[3]) < 0.02
                     and SMAP[r[4]] == u['stress'])
            if not match:
                ok = False
                print('MISMATCH', label, u, r)
    print('VALIDATION vs plan.txt:', 'ALL EXACT' if ok else 'FAILED')
    # CURRENT shipped inputs
    for label, text in [('annyeong', '%an "njVN "h\\asejo'), ('yeobo', '%jV"bo%se%jo')]:
        print('==', label, repr(text))
        units = plan_text(text)
        for i, u in enumerate(units):
            tgt = ''
            if FEAT[u['sym']][0]:
                nb = units[i+1]['sym'] if i + 1 < len(units) else None
                t = reduced(u['sym'], u['stress'] != 'U')
                if nb is not None and not FEAT[nb][0]:
                    t = locus(*t, FEAT[nb][4])
                tgt = ' target F1=%.0f F2=%.0f F3=%.0f' % t
            print('u%d sym=%s dur=%dms f0=%.2f->%.2fHz stress=%s%s'
                  % (i, u['sym'], u['dur'], u['f0'], u['f0_end'], u['stress'], tgt))
        print('total plan ms:', sum(u['dur'] for u in units))
    json.dump({l: plan_text(t) for l, t in
               [('annyeong', '%an "njVN "h\\asejo'), ('yeobo', '%jV"bo%se%jo')]},
              open('probe/0.0.0.34.1/plan-values.json', 'w'), indent=1)
    print('wrote probe/0.0.0.34.1/plan-values.json')
