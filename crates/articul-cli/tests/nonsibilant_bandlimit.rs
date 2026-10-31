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
fn solo_h_above_4k_fraction_drops_vs_baseline() {
    let h = articul_cli::render_sentence("h", 22050, 120.0);
    assert!(!h.is_empty());
    let frac = above_4k_fraction(&h, 22050);
    assert!(
        frac < 0.30,
        "solo h above-4k fraction {frac:.4} must drop below 0.30 (pre-change baseline 0.4010)"
    );
}

#[test]
fn solo_s_above_4k_fraction_unchanged() {
    let s = articul_cli::render_sentence("s", 22050, 120.0);
    assert!(!s.is_empty());
    let frac = above_4k_fraction(&s, 22050);
    assert!(
        frac > 0.90,
        "solo s above-4k fraction {frac:.4} must stay sibilant-high (baseline 0.9756)"
    );
}
