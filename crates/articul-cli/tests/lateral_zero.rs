use articul_front::parse_utterance;
use articul_front::plan_utterance;

const SR: u32 = 22050;
const N_FFT: usize = 8192;
const NOTCH_DEPTH_DB: f64 = 6.0;
const CODA_NOTCH_CEIL_DB: f64 = 3.0;

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

fn band_median(power: &[f64], lo_hz: f32, hi_hz: f32) -> f64 {
    let lo = (lo_hz / SR as f32 * N_FFT as f32).floor().max(0.0) as usize;
    let hi = (hi_hz / SR as f32 * N_FFT as f32).ceil() as usize;
    let hi = hi.min(power.len() - 1);
    let mut band = power[lo..=hi].to_vec();
    band.sort_by(|a, b| a.partial_cmp(b).unwrap());
    band[band.len() / 2]
}

fn raw_power(seg: &[f32]) -> Vec<f64> {
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
    (0..half).map(|k| re[k] * re[k] + im[k] * im[k]).collect()
}

fn notch_depth_db(power: &[f64]) -> f64 {
    let edge = band_median(power, 2000.0, 2300.0);
    let core = band_median(power, 2470.0, 2530.0);
    10.0 * (edge / core.max(1e-30)).log10()
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
fn lateral_window_has_notch() {
    let out = articul_cli::render_sentence("\"la", SR, 120.0);
    assert!(!out.is_empty());
    let seg = lateral_window(&out);
    let depth = notch_depth_db(&raw_power(&seg));
    let power = smoothed_power(&seg);
    assert!(
        depth >= NOTCH_DEPTH_DB,
        "stressed-onset lateral window must show 2-3kHz notch depth >= 6dB, got {depth:.2}dB"
    );
    let f1 = peak_near(&power, 300.0, 100.0);
    assert!(
        f1.is_some(),
        "lateral window must keep F1 peak near 300Hz within 100Hz, got {f1:?}"
    );
    let f2 = peak_near(&power, 1400.0, 200.0);
    assert!(
        f2.is_some(),
        "lateral window must keep F2 peak near 1400Hz within 200Hz, got {f2:?}"
    );
}

#[test]
fn vowel_window_scores_below_notch_floor() {
    let out = articul_cli::render_sentence("a", SR, 120.0);
    assert!(!out.is_empty());
    let n = out.len();
    let seg = out[n / 4..n * 3 / 4].to_vec();
    let depth = notch_depth_db(&raw_power(&seg));
    assert!(
        depth < NOTCH_DEPTH_DB,
        "plain vowel window must score below the 6dB notch floor, got {depth:.2}dB"
    );
}

#[test]
fn hello_interior_window_has_notch() {
    let out = articul_cli::render_sentence("hE \"loU", SR, 120.0);
    assert!(!out.is_empty());
    let lo = (170.0 * SR as f32 / 1000.0) as usize;
    let hi = (210.0 * SR as f32 / 1000.0) as usize;
    assert!(
        hi < out.len(),
        "hello interior window must fit inside output"
    );
    let seg = out[lo..hi].to_vec();
    let depth = notch_depth_db(&raw_power(&seg));
    assert!(
        depth >= NOTCH_DEPTH_DB,
        "hello interior lateral window 170-210ms must show 2-3kHz notch depth >= 6dB, got {depth:.2}dB"
    );
}

#[test]
fn coda_lateral_has_no_notch() {
    let planned = coda_planned();
    let out = articul_cli::render_sentence("pal \"art", SR, 120.0);
    assert!(!out.is_empty());
    let seg = coda_lateral_window(&out, &planned);
    let depth = notch_depth_db(&raw_power(&seg));
    assert!(
        depth < CODA_NOTCH_CEIL_DB,
        "coda lateral must not carry the onset zero, notch depth {depth:.2}dB must stay below 3dB"
    );
}
