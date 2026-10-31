use articul_dsp::ParallelFilter;

#[test]
fn zero_amplitude_gives_silence() {
    let f = ParallelFilter::from_pairs(&[(500.0, 60.0, 0.0)], 22050);
    let out = f.process(&unit_impulse(256));
    assert!(rms(&out) < 1e-6);
}

#[test]
fn amplitude_scales_linearly() {
    let lo = ParallelFilter::from_pairs(&[(500.0, 60.0, 0.4)], 22050);
    let hi = ParallelFilter::from_pairs(&[(500.0, 60.0, 0.8)], 22050);
    let x = unit_impulse(256);
    assert!((rms(&hi.process(&x)) - 2.0 * rms(&lo.process(&x))).abs() < 1e-5);
}

#[test]
fn parallel_sum_matches_single_sum() {
    let p = ParallelFilter::from_pairs(&[(500.0, 60.0, 1.0), (1500.0, 90.0, 1.0)], 22050);
    let a = ParallelFilter::from_pairs(&[(500.0, 60.0, 1.0)], 22050);
    let b = ParallelFilter::from_pairs(&[(1500.0, 90.0, 1.0)], 22050);
    let x = unit_impulse(256);
    let sum = add(&a.process(&x), &b.process(&x));
    let joint = p.process(&x);
    assert!(max_abs_diff(&sum, &joint) < 1e-5);
}

fn unit_impulse(n: usize) -> Vec<f32> {
    let mut v = vec![0.0; n];
    v[0] = 1.0;
    v
}

fn rms(x: &[f32]) -> f32 {
    (x.iter().map(|v| v * v).sum::<f32>() / x.len() as f32).sqrt()
}

fn add(a: &[f32], b: &[f32]) -> Vec<f32> {
    a.iter().zip(b.iter()).map(|(x, y)| x + y).collect()
}

fn max_abs_diff(a: &[f32], b: &[f32]) -> f32 {
    a.iter()
        .zip(b.iter())
        .map(|(x, y)| (x - y).abs())
        .fold(0.0, f32::max)
}
