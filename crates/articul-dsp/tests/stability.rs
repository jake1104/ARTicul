use articul_dsp::CascadeFilter;
use rustfft::num_complex::Complex;
use rustfft::FftPlanner;

#[test]
fn grid_stable_and_decaying() {
    let freqs = [200.0, 500.0, 1500.0, 2500.0, 3500.0, 4500.0];
    let bws = [50.0, 100.0, 200.0, 500.0];
    for f in freqs {
        for b in bws {
            let flt = CascadeFilter::single(f, b, 22050);
            let out = flt.process(&unit_impulse(2048));
            assert!(out.iter().all(|v| v.is_finite()), "non-finite f={f} b={b}");
            let tail: f32 = out[1024..].iter().map(|v| v.abs()).sum::<f32>() / 1024.0;
            assert!(tail < 0.01, "unstable f={f} b={b} tail={tail}");
        }
    }
}

#[test]
fn impulse_peak_near_formant() {
    let target = 1000.0;
    let flt = CascadeFilter::single(target, 100.0, 22050);
    let out = flt.process(&unit_impulse(2048));
    let peak = peak_freq(&out, 22050);
    assert!(
        (peak - target).abs() / target < 0.15,
        "peak={peak} target={target}"
    );
}

fn unit_impulse(n: usize) -> Vec<f32> {
    let mut v = vec![0.0; n];
    v[0] = 1.0;
    v
}

fn peak_freq(x: &[f32], sr: u32) -> f32 {
    let n = x.len();
    let mut buf: Vec<Complex<f32>> = x.iter().map(|v| Complex::new(*v, 0.0)).collect();
    let mut planner = FftPlanner::new();
    planner.plan_fft_forward(n).process(&mut buf);
    let mut best_k = 1;
    let mut best_m = 0.0;
    for (k, bin) in buf.iter().enumerate().take(n / 2).skip(1) {
        let m = bin.norm();
        if m > best_m {
            best_m = m;
            best_k = k;
        }
    }
    best_k as f32 * sr as f32 / n as f32
}
