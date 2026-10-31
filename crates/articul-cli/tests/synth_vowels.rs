use rustfft::num_complex::Complex;
use rustfft::FftPlanner;

fn band_energy(x: &[f32], sr: u32, lo: f32, hi: f32) -> f32 {
    let m = x.len().max(2);
    let n = x.len().next_power_of_two();
    let mut buf: Vec<Complex<f32>> = Vec::with_capacity(n);
    for (i, s) in x.iter().enumerate() {
        let w = 0.5 - 0.5 * (std::f32::consts::PI * 2.0 * i as f32 / m as f32).cos();
        buf.push(Complex::new(s * w, 0.0));
    }
    buf.resize(n, Complex::new(0.0, 0.0));
    FftPlanner::new().plan_fft_forward(n).process(&mut buf);
    let mut e = 0.0;
    for (k, bin) in buf.iter().enumerate().take(n / 2).skip(1) {
        let f = k as f32 * sr as f32 / n as f32;
        if (lo..=hi).contains(&f) {
            e += bin.norm_sqr() / n as f32;
        }
    }
    e
}

fn render(word: &str) -> Vec<f32> {
    articul_cli::render_sentence(word, 22050, 120.0)
}

#[test]
fn i_has_high_formant_energy_and_a_has_low() {
    let i = render("i");
    let a = render("a");
    let i_ratio = band_energy(&i, 22050, 2000.0, 2600.0) / band_energy(&i, 22050, 600.0, 900.0);
    let a_ratio = band_energy(&a, 22050, 600.0, 900.0) / band_energy(&a, 22050, 2000.0, 2600.0);
    assert!(i_ratio > 2.0, "i high/low={i_ratio}");
    assert!(a_ratio > 1.5, "a low/high={a_ratio}");
}
