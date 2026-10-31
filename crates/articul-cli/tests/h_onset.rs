use articul_front::parse_utterance;
use articul_front::plan_utterance;

const SR: u32 = 22050;
const N_FFT: usize = 8192;

fn planned_h_len() -> usize {
    let words = vec!["hE".to_string()];
    let parsed = parse_utterance(&words);
    let planned = plan_utterance(&parsed, 1.0, 1.0, 120.0);
    assert_eq!(planned.len(), 2);
    ((planned[0].duration_ms as f32 / 1000.0) * SR as f32).round() as usize
}

fn h_window(out: &[f32]) -> Vec<f32> {
    let h_len = planned_h_len();
    let lo = 150usize.min(h_len);
    let hi = h_len.saturating_sub(326).max(lo + 512);
    assert!(hi < out.len(), "h window must fit inside output");
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
fn h_carries_following_vowel_formants() {
    let out = articul_cli::render_sentence("hE", SR, 120.0);
    assert!(!out.is_empty());
    let seg = h_window(&out);
    let power = smoothed_power(&seg);
    let f1 = peak_near(&power, 576.0, 200.0);
    let f2 = peak_near(&power, 1624.0, 200.0);
    assert!(
        f1.is_some(),
        "h window must show F1 peak near 576Hz within 200Hz, got {f1:?}"
    );
    assert!(
        f2.is_some(),
        "h window must show F2 peak near 1624Hz within 200Hz, got {f2:?}"
    );
}
