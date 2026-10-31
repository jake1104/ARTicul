use articul_front::parse_utterance;
use articul_front::plan_utterance;

const SR: u32 = 22050;
const N_FFT: usize = 8192;

fn planned_lateral_ms() -> u32 {
    let words = vec!["\"la".to_string()];
    let parsed = parse_utterance(&words);
    let planned = plan_utterance(&parsed, 1.0, 1.0, 120.0);
    assert_eq!(planned.len(), 2);
    planned[0].duration_ms
}

fn lateral_window(out: &[f32]) -> Vec<f32> {
    let words = vec!["\"la".to_string()];
    let parsed = parse_utterance(&words);
    let planned = plan_utterance(&parsed, 1.0, 1.0, 120.0);
    let lens: Vec<usize> = planned
        .iter()
        .map(|u| {
            ((u.duration_ms as f32 / 1000.0) * SR as f32)
                .round()
                .max(1.0) as usize
        })
        .collect();
    let l_len = lens[0];
    let lo = 110usize.min(l_len);
    let hi = l_len.saturating_sub(176 + 110).max(lo + 512);
    assert!(hi < out.len(), "lateral window must fit inside output");
    out[lo..hi].to_vec()
}

fn smoothed_power(seg: &[f32]) -> Vec<f64> {
    let n = seg.len();
    let mut re = vec![0.0f64; N_FFT];
    let mut im = vec![0.0f64; N_FFT];
    for k in 0..N_FFT {
        let mut r = 0.0f64;
        let mut s = 0.0f64;
        for (i, v) in seg.iter().enumerate() {
            let t = i as f64 / n as f64;
            let w = 0.5 - 0.5 * (2.0 * std::f64::consts::PI * t).cos();
            let angle = 2.0 * std::f64::consts::PI * k as f64 * i as f64 / N_FFT as f64;
            r += *v as f64 * w * angle.cos();
            s -= *v as f64 * w * angle.sin();
        }
        re[k] = r;
        im[k] = s;
    }
    let half = N_FFT / 2;
    let power: Vec<f64> = (0..half).map(|k| re[k] * re[k] + im[k] * im[k]).collect();
    let smooth = 12usize;
    let mut out = vec![0.0f64; half];
    for (k, slot) in out.iter_mut().enumerate().take(half) {
        let a = k.saturating_sub(smooth);
        let b = (k + smooth + 1).min(half);
        *slot = power[a..b].iter().sum::<f64>() / (b - a) as f64;
    }
    out
}

fn peak_near(power: &[f64], target: f32, tol: f32) -> Option<f32> {
    let lo = ((target - tol) / SR as f32 * N_FFT as f32).floor().max(1.0) as usize;
    let hi = ((target + tol) / SR as f32 * N_FFT as f32).ceil() as usize;
    let hi = hi.min(power.len() - 3);
    let band = &power[lo..=hi];
    let mut sorted = band.to_vec();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let median = sorted[sorted.len() / 2];
    let mut best: Option<(f64, usize)> = None;
    for k in (lo + 2)..(hi - 1) {
        if power[k] > power[k - 1]
            && power[k] > power[k - 2]
            && power[k] >= power[k + 1]
            && power[k] >= power[k + 2]
            && power[k] > 3.0 * median
            && best.is_none_or(|(p, _)| power[k] > p)
        {
            best = Some((power[k], k));
        }
    }
    best.map(|(_, k)| k as f32 * SR as f32 / N_FFT as f32)
}

#[test]
fn lateral_has_low_f1_mid_f2() {
    let lateral_ms = planned_lateral_ms();
    assert!(
        lateral_ms >= 70,
        "pre-stressed-vowel lateral must be at least 70ms, got {lateral_ms}ms"
    );
    let lateral_samples = ((lateral_ms as f32 / 1000.0) * SR as f32).round() as usize;
    assert!(
        lateral_samples >= ((70.0 / 1000.0) * SR as f32).round() as usize,
        "rendered lateral must span at least 70ms of samples"
    );
    let out = articul_cli::render_sentence("\"la", SR, 120.0);
    assert!(!out.is_empty());
    let seg = lateral_window(&out);
    let power = smoothed_power(&seg);
    let f1 = peak_near(&power, 300.0, 100.0);
    let f2 = peak_near(&power, 1400.0, 200.0);
    assert!(
        f1.is_some(),
        "lateral window must show F1 peak near 300Hz within 100Hz, got {f1:?}"
    );
    assert!(
        f2.is_some(),
        "lateral window must show F2 peak near 1400Hz within 200Hz, got {f2:?}"
    );
}

fn coda_planned() -> Vec<articul_front::prosody::ProsodicPhoneme> {
    let words = vec!["pal".to_string(), "\"art".to_string()];
    let parsed = parse_utterance(&words);
    plan_utterance(&parsed, 1.0, 1.0, 120.0)
}

fn coda_lateral_window(
    out: &[f32],
    planned: &[articul_front::prosody::ProsodicPhoneme],
) -> Vec<f32> {
    let total = planned.len();
    let lens: Vec<usize> = planned
        .iter()
        .map(|u| {
            ((u.duration_ms as f32 / 1000.0) * SR as f32)
                .round()
                .max(1.0) as usize
        })
        .collect();
    let li = planned
        .iter()
        .position(|u| {
            matches!(
                u.phoneme.manner(),
                Some(articul_phon::Manner::LateralApproximant)
            )
        })
        .expect("coda lateral present");
    assert_eq!(planned[li].phoneme.base_symbol, "l");
    let is_vowel =
        |p: &articul_phon::Phoneme| matches!(p.kind, articul_phon::SegmentKind::Vowel { .. });
    let mut fades = vec![0usize; total];
    for i in 1..total {
        let pv = is_vowel(&planned[i - 1].phoneme);
        let cv = is_vowel(&planned[i].phoneme);
        fades[i] = if pv && cv { 1102 } else { 176 };
    }
    let mut starts = vec![0usize; total];
    for i in 1..total {
        starts[i] = starts[i - 1] + lens[i - 1] - fades[i].min(starts[i - 1]);
    }
    let margin = 110usize;
    let next_fade = if li + 1 < total { fades[li + 1] } else { 0 };
    let ws = starts[li] + fades[li] + margin;
    let we = (starts[li] + lens[li] - next_fade - margin).min(out.len());
    assert!(we > ws + 512, "coda lateral window must fit inside output");
    out[ws..we].to_vec()
}

#[test]
fn coda_lateral_keeps_neutral_targets() {
    let planned = coda_planned();
    let li = planned
        .iter()
        .position(|u| {
            matches!(
                u.phoneme.manner(),
                Some(articul_phon::Manner::LateralApproximant)
            )
        })
        .expect("coda lateral present");
    let lateral_ms = planned[li].duration_ms;
    assert!(
        lateral_ms < 70,
        "word-final coda lateral must not take the 70ms onset floor, got {lateral_ms}ms"
    );
    let out = articul_cli::render_sentence("pal \"art", SR, 120.0);
    assert!(!out.is_empty());
    let seg = coda_lateral_window(&out, &planned);
    let power = smoothed_power(&seg);
    let clear_f1 = peak_near(&power, 300.0, 100.0);
    assert!(
        clear_f1.is_none(),
        "coda lateral must not show clear-l F1 near 300Hz within 100Hz, got {clear_f1:?}"
    );
    let neutral_f1 = peak_near(&power, 500.0, 150.0);
    assert!(
        neutral_f1.is_some(),
        "coda lateral must keep neutral F1 near 500Hz within 150Hz, got {neutral_f1:?}"
    );
}
