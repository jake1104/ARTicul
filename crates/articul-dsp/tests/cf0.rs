use articul_dsp::GlottalSource;

fn src() -> GlottalSource {
    GlottalSource {
        f0_hz: 120.0,
        open_quotient: 0.6,
        asymmetry: 0.7,
        aspiration_noise: 0.0,
    }
}

fn crossings(x: &[f32], thr: f32) -> usize {
    let mut n = 0;
    for w in x.windows(2) {
        if w[0] < thr && w[1] >= thr {
            n += 1;
        }
    }
    n
}

#[test]
fn onset_factor_starts_at_plus_ten_percent() {
    assert!((articul_dsp::cf0_boost_factor(0.0) - 1.10).abs() < 1e-6);
    assert!((articul_dsp::cf0_boost_factor(0.04) - 1.10).abs() < 1e-6);
}

#[test]
fn onset_factor_decays_exponentially() {
    let at_60ms = articul_dsp::cf0_boost_factor(0.06);
    assert!((at_60ms - 1.0368).abs() < 0.002, "got {at_60ms}");
    let late = articul_dsp::cf0_boost_factor(0.5);
    assert!((late - 1.0).abs() < 0.001, "got {late}");
}

#[test]
fn cf0_onset_keeps_length_and_stays_finite() {
    let out = src().generate_cf0_onset(0.2, 22050);
    assert_eq!(out.len(), 4410);
    assert!(out.iter().all(|v| v.is_finite()));
}

#[test]
fn cf0_onset_adds_periods_up_front() {
    let out = src().generate_cf0_onset(0.2, 22050);
    let early = crossings(&out[..882], 0.5);
    let late = crossings(&out[2646..3528], 0.5);
    assert!(early >= late, "early={early} late={late}");
    assert!(early - late <= 2, "early={early} late={late}");
    let flat = src().generate(0.2, 22050);
    assert_ne!(out, flat);
}
