const SR: u32 = 22050;
const VOICE_BAND_CUTOFF_HZ: f64 = 300.0;
const VOICE_BAND_FMIN_HZ: f64 = 80.0;
const VOICE_BAND_FMAX_HZ: f64 = 300.0;
const VOICED_F0_FLOOR: f32 = 0.4;
const GENUINE_FRICATION_FLOOR: f32 = 0.8;

fn voice_bar(x: &[f32]) -> Vec<f32> {
    let a = 1.0 - (-2.0 * std::f64::consts::PI * VOICE_BAND_CUTOFF_HZ / SR as f64).exp();
    let mut y = 0.0f64;
    x.iter()
        .map(|s| {
            y += a * (*s as f64 - y);
            y as f32
        })
        .collect()
}

fn band_autocorr_peak(x: &[f32]) -> f32 {
    let mean: f32 = x.iter().sum::<f32>() / x.len().max(1) as f32;
    let v: Vec<f32> = x.iter().map(|s| s - mean).collect();
    let e0: f32 = v.iter().map(|s| s * s).sum();
    if e0 <= 1e-12 {
        return 0.0;
    }
    let lo = ((SR as f64 / VOICE_BAND_FMAX_HZ).ceil() as usize).max(1);
    let hi = ((SR as f64 / VOICE_BAND_FMIN_HZ).floor() as usize).min(v.len() - 1);
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

fn above_4k_fraction(x: &[f32], sample_rate: u32) -> f32 {
    let n = x.len();
    let mut total = 0.0f64;
    let mut high = 0.0f64;
    for k in 0..=n / 2 {
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
        total += p;
        if k as f64 * sample_rate as f64 / n as f64 >= 4000.0 {
            high += p;
        }
    }
    (high / total.max(1e-12)) as f32
}

#[test]
fn voiced_fricative_keeps_periodicity() {
    let z = articul_cli::render_sentence("z", SR, 120.0);
    assert!(!z.is_empty());
    let voice_peak = band_autocorr_peak(&voice_bar(&z));
    assert!(
        voice_peak > VOICED_F0_FLOOR,
        "solo z must stay voiced under mixed excitation, voice-band autocorr peak {voice_peak:.4}"
    );
    let frac = above_4k_fraction(&z, SR);
    assert!(
        frac > GENUINE_FRICATION_FLOOR,
        "solo z must keep genuine frication energy above 4kHz, fraction {frac:.4}"
    );
}
