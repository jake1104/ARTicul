use articul_dsp::GlottalSource;
use rustfft::num_complex::Complex;
use rustfft::FftPlanner;

fn harmonic_mags(f0: f32, oq: f32) -> Vec<(f32, f32)> {
    let src = GlottalSource {
        f0_hz: f0,
        open_quotient: oq,
        asymmetry: 0.7,
        aspiration_noise: 0.0,
    };
    let x = src.generate(1.0, 22050);
    let n = x.len();
    let mut buf: Vec<Complex<f32>> = Vec::with_capacity(n);
    for (i, s) in x.iter().enumerate() {
        let w = 0.5 - 0.5 * (std::f32::consts::PI * 2.0 * i as f32 / n as f32).cos();
        buf.push(Complex::new(s * w, 0.0));
    }
    FftPlanner::new().plan_fft_forward(n).process(&mut buf);
    let mut out = Vec::new();
    let mut h = (500.0 / f0).ceil() as u32;
    while (h as f32) * f0 <= 4000.0 {
        let fc = (h as f32) * f0;
        let klo = ((fc * 0.99) * n as f32 / 22050.0).round() as usize;
        let khi = ((fc * 1.01) * n as f32 / 22050.0).round() as usize;
        let top = khi.min(buf.len() - 1) + 1;
        let m = buf
            .iter()
            .take(top)
            .skip(klo.min(top))
            .fold(0.0f32, |a, b| a.max(b.norm()));
        out.push((fc, m));
        h += 1;
    }
    out
}

#[test]
fn no_deep_notches_in_speech_band() {
    for f0 in [90.0, 120.0, 200.0] {
        for oq in [0.4, 0.6, 0.8] {
            let hs = harmonic_mags(f0, oq);
            for (i, (f, m)) in hs.iter().enumerate() {
                let mut local: f32 = 0.0;
                for (j, (g, n)) in hs.iter().enumerate() {
                    if i != j && (g - f).abs() <= 720.0 {
                        local = local.max(*n);
                    }
                }
                let ratio = m / local.max(1e-9);
                assert!(ratio > 0.03, "notch at {f}Hz f0={f0} oq={oq} ratio={ratio}");
            }
        }
    }
}
