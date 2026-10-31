use articul_dsp::GlottalSource;

#[test]
fn pulse_train_length_matches_duration() {
    let src = GlottalSource {
        f0_hz: 120.0,
        open_quotient: 0.6,
        asymmetry: 0.7,
        aspiration_noise: 0.0,
    };
    let out = src.generate(0.1, 22050);
    assert_eq!(out.len(), 2205);
}

#[test]
fn pulse_peak_count_matches_f0() {
    let src = GlottalSource {
        f0_hz: 100.0,
        open_quotient: 0.6,
        asymmetry: 0.7,
        aspiration_noise: 0.0,
    };
    let out = src.generate(0.1, 22050);
    let peaks = count_rising_threshold_crossings(&out, 0.5);
    assert!((8..=12).contains(&peaks), "peaks={peaks}");
}

#[test]
fn aspiration_adds_energy_to_closed_phase() {
    let clean = GlottalSource {
        f0_hz: 120.0,
        open_quotient: 0.6,
        asymmetry: 0.7,
        aspiration_noise: 0.0,
    };
    let noisy = GlottalSource {
        f0_hz: 120.0,
        open_quotient: 0.6,
        asymmetry: 0.7,
        aspiration_noise: 0.3,
    };
    let a = clean.generate(0.1, 22050);
    let b = noisy.generate(0.1, 22050);
    assert_ne!(a, b);
    assert!(rms(&b) > 0.0);
}

fn count_rising_threshold_crossings(x: &[f32], thr: f32) -> usize {
    let mut n = 0;
    for w in x.windows(2) {
        if w[0] < thr && w[1] >= thr {
            n += 1;
        }
    }
    n
}

fn rms(x: &[f32]) -> f32 {
    let s: f32 = x.iter().map(|v| v * v).sum();
    (s / x.len() as f32).sqrt()
}
