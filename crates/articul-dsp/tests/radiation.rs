use articul_dsp::apply_radiation;

fn band(x: &[f32], sr: u32, lo: f32, hi: f32) -> f32 {
    use rustfft::num_complex::Complex;
    use rustfft::FftPlanner;
    let n = x.len().next_power_of_two();
    let mut buf: Vec<Complex<f32>> = Vec::with_capacity(n);
    for (i, s) in x.iter().enumerate() {
        let w = 0.5 - 0.5 * (std::f32::consts::PI * 2.0 * i as f32 / x.len() as f32).cos();
        buf.push(Complex::new(s * w, 0.0));
    }
    buf.resize(n, Complex::new(0.0, 0.0));
    FftPlanner::new().plan_fft_forward(n).process(&mut buf);
    let mut e = 0.0;
    for (k, b) in buf.iter().enumerate().take(n / 2).skip(1) {
        let f = k as f32 * sr as f32 / n as f32;
        if (lo..=hi).contains(&f) {
            e += b.norm_sqr();
        }
    }
    e
}

#[test]
fn radiation_lifts_highs_about_6db_per_oct() {
    let sr = 22050u32;
    let n = 4096usize;
    let lo: Vec<f32> = (0..n)
        .map(|i| (2.0 * std::f32::consts::PI * 1000.0 * i as f32 / sr as f32).sin())
        .collect();
    let hi: Vec<f32> = (0..n)
        .map(|i| (2.0 * std::f32::consts::PI * 2000.0 * i as f32 / sr as f32).sin())
        .collect();
    let lo_in = band(&lo, sr, 900.0, 1100.0);
    let hi_in = band(&hi, sr, 1900.0, 2100.0);
    let lo_out = band(&apply_radiation(&lo), sr, 900.0, 1100.0);
    let hi_out = band(&apply_radiation(&hi), sr, 1900.0, 2100.0);
    let tilt_in = hi_in / lo_in;
    let tilt_out = hi_out / lo_out;
    let boost_db = 10.0 * (tilt_out / tilt_in).log10();
    assert!(
        (4.0..=8.0).contains(&boost_db),
        "expected about +6dB/oct, got {boost_db:.1}dB"
    );
}

#[test]
fn radiation_preserves_length_and_finiteness() {
    let x = vec![0.0, 0.5, -0.25, 0.125, 0.0, 0.0, 0.0, 0.0];
    let y = apply_radiation(&x);
    assert_eq!(y.len(), x.len());
    assert!(y.iter().all(|v| v.is_finite()));
}
