use articul_dsp::GlottalSource;

fn src(f0: f32) -> GlottalSource {
    GlottalSource {
        f0_hz: f0,
        open_quotient: 0.6,
        asymmetry: 0.7,
        aspiration_noise: 0.0,
    }
}

fn crossing_intervals(x: &[f32], thr: f32) -> Vec<usize> {
    let mut crosses = Vec::new();
    for (i, w) in x.windows(2).enumerate() {
        if w[0] < thr && w[1] >= thr {
            crosses.push(i);
        }
    }
    crosses.windows(2).map(|w| w[1] - w[0]).collect()
}

fn edge_mean(iv: &[usize]) -> (f32, f32) {
    let first = iv[..5].iter().sum::<usize>() as f32 / 5.0;
    let last = iv[iv.len() - 5..].iter().sum::<usize>() as f32 / 5.0;
    (first, last)
}

#[test]
fn glide_keeps_length_and_stays_finite() {
    let out = src(120.0).generate_glide(0.2, 22050, 100.0);
    assert_eq!(out.len(), 4410);
    assert!(out.iter().all(|v| v.is_finite()));
}

#[test]
fn falling_glide_lengthens_periods() {
    let out = src(132.0).generate_glide(0.2, 22050, 108.0);
    let (first, last) = edge_mean(&crossing_intervals(&out, 0.5));
    assert!(last > first * 1.1, "first={first} last={last}");
}

#[test]
fn rising_glide_shortens_periods() {
    let out = src(108.0).generate_glide(0.2, 22050, 132.0);
    let (first, last) = edge_mean(&crossing_intervals(&out, 0.5));
    assert!(last * 1.1 < first, "first={first} last={last}");
}

#[test]
fn flat_glide_matches_flat_period_count() {
    let glided = src(120.0).generate_glide(0.2, 22050, 120.0);
    let flat = src(120.0).generate(0.2, 22050);
    assert_eq!(
        crossing_intervals(&glided, 0.5).len(),
        crossing_intervals(&flat, 0.5).len()
    );
}
