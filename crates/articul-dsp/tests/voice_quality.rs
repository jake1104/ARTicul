use articul_dsp::GlottalSource;

fn src() -> GlottalSource {
    GlottalSource {
        f0_hz: 120.0,
        open_quotient: 0.6,
        asymmetry: 0.7,
        aspiration_noise: 0.0,
    }
}

fn rising_intervals(x: &[f32], thr: f32) -> Vec<usize> {
    let mut crosses = Vec::new();
    for (i, w) in x.windows(2).enumerate() {
        if w[0] < thr && w[1] >= thr {
            crosses.push(i);
        }
    }
    crosses.windows(2).map(|w| w[1] - w[0]).collect()
}

fn stddev(v: &[usize]) -> f32 {
    let mean = v.iter().sum::<usize>() as f32 / v.len().max(1) as f32;
    (v.iter().map(|x| (*x as f32 - mean).powi(2)).sum::<f32>() / v.len().max(1) as f32).sqrt()
}

#[test]
fn jitter_adds_period_variance() {
    let out = src().generate(0.5, 22050);
    let iv = rising_intervals(&out, 0.5);
    assert!(stddev(&iv) > 0.5, "std=0 means no jitter");
}

#[test]
fn output_stays_deterministic() {
    let a = src().generate(0.2, 22050);
    let b = src().generate(0.2, 22050);
    assert_eq!(a, b);
}

#[test]
fn shimmer_varies_peak_amplitude() {
    let out = src().generate(0.3, 22050);
    let mut peaks = Vec::new();
    let mut cur = 0.0f32;
    for w in out.windows(2) {
        if w[0] <= w[1] {
            cur = w[1];
        } else {
            if cur > 0.5 {
                peaks.push(cur);
            }
            cur = w[1];
        }
    }
    let mean = peaks.iter().sum::<f32>() / peaks.len().max(1) as f32;
    let sd =
        (peaks.iter().map(|p| (p - mean).powi(2)).sum::<f32>() / peaks.len().max(1) as f32).sqrt();
    assert!(sd / mean.max(1e-9) > 0.005, "cv={}", sd / mean.max(1e-9));
}

#[test]
fn breathiness_follows_glottal_cycle() {
    let clean = GlottalSource {
        aspiration_noise: 0.0,
        ..src()
    }
    .generate(0.3, 22050);
    let noisy = GlottalSource {
        aspiration_noise: 1.0,
        ..src()
    }
    .generate(0.3, 22050);
    assert_eq!(clean.len(), noisy.len());
    let mut hi = 0.0f32;
    let mut lo = 0.0f32;
    let mut nhi = 0usize;
    let mut nlo = 0usize;
    for i in 0..clean.len() {
        let flow = clean[i].clamp(0.0, 1.0);
        let nz = (noisy[i] - clean[i]).abs();
        if flow > 0.5 {
            hi += nz * nz;
            nhi += 1;
        } else if flow < 0.2 {
            lo += nz * nz;
            nlo += 1;
        }
    }
    let ratio = (hi / nhi.max(1) as f32) / (lo / nlo.max(1) as f32);
    assert!(ratio > 1.4, "high-flow/low-flow noise={ratio}");
}

#[test]
fn creak_alternates_periods() {
    let out = src().generate_creak(0.3, 22050);
    assert_eq!(out.len(), 6615);
    let iv = rising_intervals(&out, 0.05);
    let tail = &iv[iv.len() - 10..];
    let hi = *tail.iter().max().unwrap() as f32;
    let lo = (*tail.iter().min().unwrap()).max(1) as f32;
    assert!(hi / lo > 1.25, "max={hi} min={lo}");
}
