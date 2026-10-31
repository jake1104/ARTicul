use articul_front::parse_utterance;
use articul_front::plan_utterance;

const SR: u32 = 22050;

fn hello_units() -> Vec<articul_front::prosody::ProsodicPhoneme> {
    let words = vec!["hE".to_string(), "\"loU".to_string()];
    let parsed = parse_utterance(&words);
    plan_utterance(&parsed, 1.0, 1.0, 120.0)
}

fn is_vowel(p: &articul_phon::Phoneme) -> bool {
    matches!(p.kind, articul_phon::SegmentKind::Vowel { .. })
}

fn diphthong_span_start(
    lens: &[usize],
    vowels: &[bool],
    planned: &[articul_front::prosody::ProsodicPhoneme],
) -> usize {
    let mut starts = vec![0usize; lens.len()];
    for i in 1..lens.len() {
        let fade = if vowels[i - 1] && vowels[i] {
            1102usize
        } else {
            176usize
        };
        starts[i] = starts[i - 1] + lens[i - 1] - fade.min(starts[i - 1]);
    }
    let oi = planned
        .iter()
        .position(|u| u.phoneme.base_symbol == "o" && u.stress != articul_front::Stress::Unstressed)
        .unwrap_or(lens.len() - 2);
    let fade_in = if oi > 0 && vowels[oi - 1] && vowels[oi] {
        1102usize
    } else {
        176usize
    };
    starts[oi] + fade_in + 110
}

fn estimate_f2(x: &[f32]) -> f32 {
    let n = x.len();
    let mut best_f = 0.0f32;
    let mut best_p = -1.0f64;
    let mut k = ((700.0 * n as f32 / SR as f32).ceil() as usize).max(1);
    let k_end = (1500.0 * n as f32 / SR as f32).floor() as usize;
    while k <= k_end.min(n / 2) {
        let mut re = 0.0f64;
        let mut im = 0.0f64;
        for (i, v) in x.iter().enumerate() {
            let t = i as f64 / n as f64;
            let w = 0.5 - 0.5 * (2.0 * std::f64::consts::PI * t).cos();
            let angle = 2.0 * std::f64::consts::PI * k as f64 * t;
            re += *v as f64 * w * angle.cos();
            im -= *v as f64 * w * angle.sin();
        }
        let p = re * re + im * im;
        if p > best_p {
            best_p = p;
            best_f = k as f32 * SR as f32 / n as f32;
        }
        k += 1;
    }
    best_f
}

fn f2_trajectory(out: &[f32], start: usize) -> Vec<f32> {
    let span = &out[start..];
    let nw = 6usize;
    let wlen = span.len() / nw;
    (0..nw)
        .map(|w| {
            let s = w * wlen;
            let e = (s + wlen).min(span.len());
            estimate_f2(&span[s..e])
        })
        .collect()
}

fn autocorr_peak(x: &[f32]) -> f32 {
    let mean: f32 = x.iter().sum::<f32>() / x.len().max(1) as f32;
    let v: Vec<f32> = x.iter().map(|s| s - mean).collect();
    let e0: f32 = v.iter().map(|s| s * s).sum();
    if e0 <= 1e-12 {
        return 0.0;
    }
    let lo = (SR as usize / 300).max(1);
    let hi = (SR as usize / 60).min(v.len() - 1);
    let mut best = 0.0f32;
    for lag in lo..=hi {
        let mut acc = 0.0f32;
        for i in 0..v.len() - lag {
            acc += v[i] * v[i + lag];
        }
        best = best.max(acc / e0);
    }
    best
}

#[test]
fn diphthong_f2_rises_monotonically() {
    let out = articul_cli::render_sentence("hE \"loU", SR, 120.0);
    assert!(!out.is_empty());
    assert!(!out.is_empty());
    let planned = hello_units();
    let lens: Vec<usize> = planned
        .iter()
        .map(|u| {
            ((u.duration_ms as f32 / 1000.0) * SR as f32)
                .round()
                .max(1.0) as usize
        })
        .collect();
    let vowels: Vec<bool> = planned.iter().map(|u| is_vowel(&u.phoneme)).collect();
    let start = diphthong_span_start(&lens, &vowels, &planned);
    assert!(start + 1000 < out.len());
    let f2 = f2_trajectory(&out, start);
    assert_eq!(f2.len(), 6);
    for w in f2.windows(2) {
        assert!(
            w[1] >= w[0] - 50.0,
            "F2 must rise monotonically within 50Hz tolerance, got {f2:?}"
        );
    }
    assert!(
        f2[5] - f2[0] >= 100.0,
        "F2 must rise overall by at least 100Hz across the o+U glide, got {f2:?}"
    );
}

#[test]
fn diphthong_final_80ms_stays_periodic() {
    let out = articul_cli::render_sentence("hE \"loU", SR, 120.0);
    assert!(!out.is_empty());
    let tail = ((0.080 * SR as f32) as usize).min(out.len());
    let seg = &out[out.len() - tail..];
    let peak = autocorr_peak(seg);
    assert!(
        peak > 0.5,
        "final 80ms must stay periodic without creak, autocorr peak {peak:.3}"
    );
}
