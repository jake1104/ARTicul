use articul_front::parse_utterance;
use articul_front::plan_utterance;
use articul_front::prosody::ProsodicPhoneme;
use articul_phon::Manner;

const SR: u32 = 22050;
const F0: f32 = 120.0;
const INPUTS: [&str; 3] = ["hE \"loU", "%an njVN \"hasejo", "%jV\"bo%se%jo"];
const BASE_RMS: [f32; 3] = [0.183119, 0.103675, 0.114574];
const FRAME: usize = 882;
const STEP: usize = 441;
const EDGE: usize = 220;
const MIN_INTERIOR: usize = 1323;
const HALVES_TILT_BOUND: f32 = 4.0;
const RATIO_BOUND: f32 = 3.0;

fn is_vowel_unit(u: &ProsodicPhoneme) -> bool {
    matches!(u.phoneme.kind, articul_phon::SegmentKind::Vowel { .. })
}

fn is_goat_onset(u: &ProsodicPhoneme) -> bool {
    !u.is_pause
        && u.stress != articul_front::Stress::Unstressed
        && u.phoneme.base_symbol == "o"
        && matches!(
            u.phoneme.kind,
            articul_phon::SegmentKind::Vowel { rounded: true, .. }
        )
}

fn is_goat_offglide(u: &ProsodicPhoneme) -> bool {
    !u.is_pause
        && u.stress == articul_front::Stress::Unstressed
        && u.phoneme.base_symbol == "\u{028A}"
        && matches!(u.phoneme.kind, articul_phon::SegmentKind::Vowel { .. })
}

fn work_groups(planned: &[ProsodicPhoneme]) -> Vec<Vec<usize>> {
    let mut groups: Vec<Vec<usize>> = Vec::new();
    let mut i = 0usize;
    while i < planned.len() {
        if i + 1 < planned.len() && is_goat_onset(&planned[i]) && is_goat_offglide(&planned[i + 1])
        {
            groups.push(vec![i, i + 1]);
            i += 2;
        } else {
            groups.push(vec![i]);
            i += 1;
        }
    }
    groups
}

fn group_len_ms(planned: &[ProsodicPhoneme], group: &[usize]) -> u32 {
    group.iter().map(|oi| planned[*oi].duration_ms).sum()
}

fn samples(ms: u32) -> usize {
    ((ms as f32 / 1000.0) * SR as f32).round().max(1.0) as usize
}

fn in_voiced_set(u: &ProsodicPhoneme) -> bool {
    if u.is_pause {
        return false;
    }
    if is_vowel_unit(u) {
        return true;
    }
    if !u.phoneme.is_voiced() {
        return false;
    }
    matches!(
        u.phoneme.manner(),
        Some(
            Manner::Nasal
                | Manner::Trill
                | Manner::TapFlap
                | Manner::Approximant
                | Manner::LateralApproximant
        )
    )
}

fn band_energy(x: &[f32], lo_hz: f32, hi_hz: f32) -> f64 {
    let n = x.len();
    let sr = SR as f64;
    let mut e = 0.0f64;
    for k in 1..=n / 2 {
        let f = k as f64 * sr / n as f64;
        if f < lo_hz as f64 || f >= hi_hz as f64 {
            continue;
        }
        let mut re = 0.0f64;
        let mut im = 0.0f64;
        for (i, v) in x.iter().enumerate() {
            let a = 2.0 * std::f64::consts::PI * k as f64 * i as f64 / n as f64;
            re += *v as f64 * a.cos();
            im -= *v as f64 * a.sin();
        }
        e += re * re + im * im;
    }
    e
}

fn total_energy(x: &[f32]) -> f64 {
    x.iter().map(|v| (*v as f64) * (*v as f64)).sum()
}

fn hf_frac(x: &[f32]) -> f64 {
    let t = total_energy(x).max(1e-18);
    let n = x.len() as f64;
    2.0 * band_energy(x, 4000.0, SR as f32 / 2.0) / n / t
}

fn tilt_db(x: &[f32]) -> f32 {
    let lo = band_energy(x, 0.0, 1000.0).max(1e-18);
    let hi = band_energy(x, 4000.0, SR as f32 / 2.0).max(1e-18);
    (10.0 * (lo / hi).log10()) as f32
}

fn median(mut v: Vec<f64>) -> f64 {
    v.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let n = v.len();
    if n % 2 == 1 {
        v[n / 2]
    } else {
        0.5 * (v[n / 2 - 1] + v[n / 2])
    }
}

fn analyze(text: &str) -> (f32, f64, f64, String) {
    let words: Vec<String> = articul_front::normalize(text);
    let parsed = parse_utterance(&words);
    let planned = plan_utterance(&parsed, 1.0, 1.0, F0);
    let out = articul_cli::render_sentence(text, SR, F0);
    assert!(!out.is_empty());
    let groups = work_groups(&planned);
    let lens: Vec<usize> = groups
        .iter()
        .map(|g| samples(group_len_ms(&planned, g)))
        .collect();
    let fades: Vec<usize> = groups
        .iter()
        .enumerate()
        .map(|(gi, group)| {
            if gi == 0 {
                0
            } else {
                let left_v = is_vowel_unit(&planned[groups[gi - 1][0]]);
                let right_v = is_vowel_unit(&planned[group[0]]);
                if left_v && right_v {
                    1102
                } else {
                    176
                }
            }
        })
        .collect();
    let total: usize = lens.iter().sum::<usize>() - fades.iter().sum::<usize>();
    assert_eq!(
        total,
        out.len(),
        "concat arithmetic mismatch for {text}: predicted {total} vs rendered {}",
        out.len()
    );
    let rms = (out.iter().map(|v| v * v).sum::<f32>() / out.len() as f32).sqrt();
    let mut pos = 0usize;
    let mut detail = String::new();
    let mut full_means: Vec<f64> = Vec::new();
    let mut gated: Vec<f64> = Vec::new();
    for (gi, group) in groups.iter().enumerate() {
        let next_fade = if gi + 1 < groups.len() {
            fades[gi + 1]
        } else {
            0
        };
        let start = pos;
        let end = pos + lens[gi] - next_fade;
        pos = end;
        let u = &planned[group[0]];
        if !in_voiced_set(u) {
            continue;
        }
        let splits: Vec<(usize, usize, usize)> = if group.len() == 2 {
            let cut = (start + samples(planned[group[0]].duration_ms)).min(end);
            vec![(group[0], start, cut), (group[1], cut, end)]
        } else {
            vec![(group[0], start, end)]
        };
        for (oi, a, b) in splits {
            let su = &planned[oi];
            if b < a + 2 * EDGE + FRAME {
                continue;
            }
            let interior = &out[a + EDGE..b - EDGE];
            if interior.len() < MIN_INTERIOR {
                continue;
            }
            let mut fracs: Vec<f64> = Vec::new();
            let mut k = 0usize;
            while k + FRAME <= interior.len() {
                fracs.push(hf_frac(&interior[k..k + FRAME]));
                k += STEP;
            }
            if fracs.is_empty() {
                continue;
            }
            let mean: f64 = fracs.iter().sum::<f64>() / fracs.len() as f64;
            full_means.push(mean);
            let med = median(fracs.clone());
            let half = interior.len() / 2;
            let t1 = tilt_db(&interior[..half]);
            let t2 = tilt_db(&interior[half..]);
            let stable = (t1 - t2).abs() <= HALVES_TILT_BOUND;
            detail.push_str(&format!(
                "{text} g{gi}u{oi} {} interior={}ms nfr={} mean_hf={:.5} med_hf={:.5} tilt={:.1}/{:.1} stable={stable}\n",
                su.phoneme.base_symbol,
                interior.len() * 1000 / SR as usize,
                fracs.len(),
                mean,
                med,
                t1,
                t2
            ));
            if stable {
                gated.push(med);
            }
        }
    }
    let full_ratio = if full_means.len() >= 2 {
        let mx = full_means.iter().cloned().fold(0.0f64, f64::max);
        let mn = full_means.iter().cloned().fold(f64::MAX, f64::min);
        mx / mn.max(1e-18)
    } else {
        1.0
    };
    let gated_ratio = if gated.len() >= 2 {
        let mx = gated.iter().cloned().fold(0.0f64, f64::max);
        let mn = gated.iter().cloned().fold(f64::MAX, f64::min);
        mx / mn.max(1e-18)
    } else {
        1.0
    };
    (rms, full_ratio, gated_ratio, detail)
}

#[test]
fn bed_variance_bounded() {
    let mut report = String::new();
    let mut rows: Vec<(f32, f64, f64)> = Vec::new();
    for text in INPUTS {
        let (rms, full_ratio, gated_ratio, detail) = analyze(text);
        report.push_str(&format!(
            "{text}: rms={rms:.6} full_mean_ratio={full_ratio:.2} gated_median_ratio={gated_ratio:.2}\n{detail}"
        ));
        rows.push((rms, full_ratio, gated_ratio));
    }
    eprintln!("{report}");
    for (di, text) in INPUTS.iter().enumerate() {
        let (rms, mean_ratio, _med_ratio) = rows[di];
        let lift = 20.0 * (rms / BASE_RMS[di].max(1e-9)).log10();
        assert!(
            lift <= 1.0,
            "global RMS lift {lift:.2}dB > +1dB vs pre-bed baseline for {text}\n{report}"
        );
        assert!(
            mean_ratio <= RATIO_BOUND as f64,
            "segment HF-fraction max/min {mean_ratio:.2} > {:.1} for {text}\n{report}",
            RATIO_BOUND
        );
    }
}
