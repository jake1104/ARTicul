use rustfft::num_complex::Complex;
use rustfft::FftPlanner;

pub fn spectral_slope_db_per_oct(samples: &[f32], sample_rate: u32) -> f32 {
    let n = 8192.min(samples.len());
    let n = n.next_power_of_two().min(samples.len());
    let mut buf: Vec<Complex<f32>> = Vec::with_capacity(n);
    for (i, sample) in samples.iter().enumerate().take(n) {
        let w = 0.5 - 0.5 * (std::f32::consts::PI * 2.0 * i as f32 / n as f32).cos();
        buf.push(Complex::new(sample * w, 0.0));
    }
    let mut planner = FftPlanner::new();
    let fft = planner.plan_fft_forward(n);
    fft.process(&mut buf);
    let sr = sample_rate as f32;
    let mut xs = Vec::new();
    let mut ys = Vec::new();
    for (k, bin) in buf.iter().enumerate().take(n / 2).skip(1) {
        let freq = k as f32 * sr / n as f32;
        if !(100.0..=4000.0).contains(&freq) {
            continue;
        }
        let mag = bin.norm() / n as f32 + 1e-12;
        xs.push(freq.log2());
        ys.push(20.0 * mag.log10());
    }
    linear_slope(&xs, &ys)
}

fn linear_slope(xs: &[f32], ys: &[f32]) -> f32 {
    let n = xs.len() as f32;
    if n < 2.0 {
        return 0.0;
    }
    let mx: f32 = xs.iter().sum::<f32>() / n;
    let my: f32 = ys.iter().sum::<f32>() / n;
    let mut num = 0.0;
    let mut den = 0.0;
    for (x, y) in xs.iter().zip(ys.iter()) {
        num += (x - mx) * (y - my);
        den += (x - mx) * (x - mx);
    }
    if den == 0.0 {
        0.0
    } else {
        num / den
    }
}
