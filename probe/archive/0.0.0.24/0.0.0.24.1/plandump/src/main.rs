// Plan dump for task 0.0.0.24.1 (read-only probe, no engine change).
// Dumps the front-end plan + probe-side boundary classification that mirrors
// synth.rs logic (is_goat_pair, VV check, spec_for kind routing, fade sizes,
// GOAT merge length, fade clamps) so junctions.py can place exact boundaries.

use articul_front::{plan_utterance, Stress};
use articul_phon::{Manner, Place, SegmentKind};

const SR: u32 = 22050;
const SHORT: usize = 176; // (0.008 * 22050) as usize
const GLIDE: usize = 1102; // (0.050 * 22050) as usize

fn is_vowel(p: &articul_phon::Phoneme) -> bool {
    matches!(p.kind, SegmentKind::Vowel { .. })
}

fn is_fricative(p: &articul_phon::Phoneme) -> bool {
    matches!(
        p.manner(),
        Some(Manner::Fricative | Manner::LateralFricative)
    )
}

fn is_h_onset(p: &articul_phon::Phoneme) -> bool {
    !p.is_voiced()
        && matches!(p.manner(), Some(Manner::Fricative))
        && matches!(p.place(), Some(Place::Glottal))
}

fn is_lateral_onset(p: &articul_phon::Phoneme) -> bool {
    matches!(p.manner(), Some(Manner::LateralApproximant))
}

fn is_goat_onset(
    p: &articul_phon::Phoneme,
    s: Stress,
    pause: bool,
) -> bool {
    !pause
        && !matches!(s, Stress::Unstressed)
        && p.base_symbol == "o"
        && matches!(p.kind, SegmentKind::Vowel { rounded: true, .. })
}

fn is_goat_offglide(
    p: &articul_phon::Phoneme,
    s: Stress,
    pause: bool,
) -> bool {
    !pause
        && matches!(s, Stress::Unstressed)
        && p.base_symbol == "\u{028A}"
        && matches!(p.kind, SegmentKind::Vowel { .. })
}

// Mirror of spec_for kind routing (synth.rs): Cascade unless a non-h,
// non-clear-lateral fricative (which routes to Parallel).
fn spec_kind(
    idx: usize,
    units: &[articul_front::prosody::ProsodicPhoneme],
) -> &'static str {
    let u = &units[idx];
    let n = units.len();
    let next = if idx + 1 < n { Some(&units[idx + 1]) } else { None };
    let prev = if idx > 0 { Some(&units[idx - 1]) } else { None };
    let mut neighbor = next
        .filter(|p| !is_vowel(&p.phoneme))
        .or(prev.filter(|p| !is_vowel(&p.phoneme)));
    if is_h_onset(&u.phoneme) || is_lateral_onset(&u.phoneme) {
        neighbor = next.filter(|p| is_vowel(&p.phoneme)).or(neighbor);
    }
    if is_h_onset(&u.phoneme) {
        if let Some(nb) = neighbor {
            if is_vowel(&nb.phoneme) {
                return "Cascade";
            }
        }
    }
    if is_lateral_onset(&u.phoneme) && !u.word_final {
        if let Some(nb) = neighbor {
            if is_vowel(&nb.phoneme) && !matches!(nb.stress, Stress::Unstressed) {
                return "Cascade";
            }
        }
    }
    if is_fricative(&u.phoneme) {
        return "Parallel";
    }
    "Cascade"
}

fn dump(text: &str, label: &str) {
    let words = articul_front::normalize(text);
    let parsed = articul_front::parse_utterance(&words);
    let units = plan_utterance(&parsed, 1.0, 1.0, 120.0);
    let total = units.len();
    println!("== {} :: {}", label, text);
    println!("units={}", total);
    for (i, u) in units.iter().enumerate() {
        let seg_len = ((u.duration_ms as f32 / 1000.0) * SR as f32)
            .round()
            .max(1.0) as usize;
        let g = articul_cli::segment_gain_db(u, i, total);
        let kind = spec_kind(i, &units);
        println!(
            "u{} sym={} dur={}ms f0={:.2}->{:.2}Hz stress={:?} word_final={} pause={} spec={} seglen={} gain={:.3}dB",
            i,
            u.phoneme.base_symbol,
            u.duration_ms,
            u.f0_hz,
            u.f0_end_hz,
            u.stress,
            u.word_final,
            u.is_pause,
            kind,
            seg_len,
            g
        );
    }
    // Work units with GOAT merge (mirror of render_units).
    let mut work: Vec<Vec<usize>> = Vec::new();
    let mut i = 0usize;
    while i < total {
        if i + 1 < total
            && is_goat_onset(&units[i].phoneme, units[i].stress, units[i].is_pause)
            && is_goat_offglide(
                &units[i + 1].phoneme,
                units[i + 1].stress,
                units[i + 1].is_pause,
            )
        {
            work.push(vec![i, i + 1]);
            i += 2;
        } else {
            work.push(vec![i]);
            i += 1;
        }
    }
    let mut lens: Vec<usize> = Vec::new();
    for w in work.iter() {
        if w.len() == 2 {
            let ms = units[w[0]].duration_ms + units[w[1]].duration_ms;
            lens.push(((ms as f32 / 1000.0) * SR as f32).round().max(1.0) as usize);
        } else {
            let ms = units[w[0]].duration_ms;
            lens.push(((ms as f32 / 1000.0) * SR as f32).round().max(1.0) as usize);
        }
    }
    // Fades between work units: VV -> GLIDE else SHORT (mirror).
    let is_work_vowel = |w: &Vec<usize>| -> bool {
        is_vowel(&units[w[0]].phoneme)
    };
    let mut fades = vec![0usize; work.len()];
    for k in 0..work.len().saturating_sub(1) {
        fades[k + 1] = if is_work_vowel(&work[k]) && is_work_vowel(&work[k + 1]) {
            GLIDE
        } else {
            SHORT
        };
    }
    // Boundary positions with engine-identical clamps (mirror concat loop).
    let mut out_len = 0usize;
    let mut pos: Vec<usize> = Vec::new();
    for (idx, len) in lens.iter().enumerate() {
        let want = if idx == 0 { 0 } else { fades[idx] };
        let n = want.min(*len).min(out_len);
        if idx > 0 {
            pos.push(out_len - n);
        }
        out_len = out_len - n + len;
        let _ = n;
    }
    println!(
        "work_units={} lens={:?} fades={:?} predicted_out_len={}",
        work
            .iter()
            .map(|w| format!("{:?}", w))
            .collect::<Vec<_>>()
            .join(" "),
        lens,
        fades,
        out_len
    );
    for (b, w) in work.iter().enumerate().skip(1) {
        let prev = &work[b - 1];
        let zone_start = pos[b - 1];
        let n = fades[b].min(lens[b]).min(
            lens[..b].iter().sum::<usize>() - fades[1..b].iter().sum::<usize>(),
        );
        let a_last = *prev.last().unwrap();
        let b_first = w[0];
        let g_prev = articul_cli::segment_gain_db(&units[a_last], a_last, total);
        let g_next = articul_cli::segment_gain_db(&units[b_first], b_first, total);
        let f_prev = units[a_last].f0_end_hz;
        let f_next = units[b_first].f0_hz;
        let st = 12.0 * (f_next / f_prev.max(1e-6)).log2();
        // can_glide mirror: same spec kind; parallel len check via shaping table.
        let ka = spec_kind(a_last, &units);
        let kb = spec_kind(b_first, &units);
        let glide_ok = if ka != kb {
            false
        } else if ka == "Parallel" {
            articul_dsp::fricative_shaping(&units[a_last].phoneme).len()
                == articul_dsp::fricative_shaping(&units[b_first].phoneme).len()
        } else {
            true
        };
        let btype = if prev.len() == 2 || w.len() == 2 {
            "GOAT-EDGE"
        } else if is_vowel(&units[a_last].phoneme) && is_vowel(&units[b_first].phoneme) {
            "VV-GLIDE"
        } else if glide_ok {
            "CASCADE-SHORT-GLIDE"
        } else {
            "MIXED-LINEAR"
        };
        println!(
            "b{} between u{}({})->u{}({}) type={} zone=[{}, {}) n={} gain_step={:.3}dB f0_step={:.3}st",
            b,
            a_last,
            units[a_last].phoneme.base_symbol,
            b_first,
            units[b_first].phoneme.base_symbol,
            btype,
            zone_start,
            zone_start + n,
            n,
            (g_next - g_prev).abs(),
            st
        );
    }
}

fn main() {
    println!("SR={} SHORT={} GLIDE={}", SR, SHORT, GLIDE);
    dump("hE \"loU", "hello");
    dump("%an njVN \"hasejo", "annyeong");
    dump("%jV\"bo%se%jo", "yeobo");
}
