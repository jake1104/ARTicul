use articul_dsp::GlottalSource;

const SR: u32 = 22050;
const F0: f32 = 149.0;
const REG_A: usize = 441;
const REG_B: usize = 3087;
const FRAME_LEN: usize = 441;
const FRAME_HOP: usize = 441;
const WIN_LEN: usize = 441;
const WIN_HOP: usize = 100;

fn flat_source() -> GlottalSource {
    GlottalSource {
        f0_hz: F0,
        open_quotient: 0.6,
        asymmetry: 0.7,
        aspiration_noise: 0.0,
    }
}

fn voiced_source() -> GlottalSource {
    GlottalSource {
        f0_hz: F0,
        open_quotient: 0.6,
        asymmetry: 0.7,
        aspiration_noise: 0.05,
    }
}

fn corr_periods(x: &[f32]) -> Vec<f32> {
    let t0n = SR as f32 / F0;
    let h = 60usize;
    let tbase = 700usize;
    let tmpl: Vec<f32> = (0..(2 * h + 21)).map(|m| x[tbase - 70 + m]).collect();
    let mut shifts: Vec<f32> = Vec::new();
    let mut k = 0usize;
    loop {
        let a = tbase as f32 + k as f32 * t0n;
        let ai = a.round() as usize;
        if ai < h || ai + h + 1 >= x.len() {
            break;
        }
        let seg: Vec<f32> = (0..(2 * h + 1)).map(|j| x[ai - h + j]).collect();
        let mut cv = Vec::with_capacity(21);
        for s in -10i32..=10i32 {
            let mut acc = 0.0f32;
            for j in 0..seg.len() {
                acc += seg[j] * tmpl[(j as i32 + 10 + s) as usize];
            }
            cv.push(acc);
        }
        let mut bi = 0usize;
        let mut bvv = f32::NEG_INFINITY;
        for (i, v) in cv.iter().enumerate() {
            if *v > bvv {
                bvv = *v;
                bi = i;
            }
        }
        let bg = if bi > 0 && bi + 1 < cv.len() {
            let d = cv[bi - 1] - 2.0 * cv[bi] + cv[bi + 1];
            if d.abs() > 1e-12 {
                0.5 * (cv[bi - 1] - cv[bi + 1]) / d
            } else {
                0.0
            }
        } else {
            0.0
        };
        shifts.push((bi as f32 - 10.0) + bg.clamp(-1.0, 1.0));
        k += 1;
    }
    shifts.windows(2).map(|w| t0n + w[1] - w[0]).collect()
}

fn local_jitter(periods: &[f32]) -> f32 {
    let mean = periods.iter().sum::<f32>() / periods.len() as f32;
    let diff =
        periods.windows(2).map(|w| (w[1] - w[0]).abs()).sum::<f32>() / (periods.len() - 1) as f32;
    diff / mean
}

fn autocorr_f0(seg: &[f32]) -> Option<f32> {
    autocorr_f0_tracked(seg, None)
}

fn autocorr_f0_tracked(seg: &[f32], guess: Option<f32>) -> Option<f32> {
    let mean = seg.iter().sum::<f32>() / seg.len() as f32;
    let x: Vec<f32> = seg.iter().map(|v| v - mean).collect();
    let e0: f32 = x.iter().map(|v| v * v).sum();
    if e0 <= 1e-12 {
        return None;
    }
    let (lo, hi) = match guess {
        Some(g) => {
            let c = SR as f32 / g;
            ((c / 1.12) as usize, (c * 1.12) as usize)
        }
        None => (
            (SR as f32 / 250.0).round() as usize,
            (SR as f32 / 70.0).round() as usize,
        ),
    };
    let top = hi.min(x.len() - 1);
    if top <= lo {
        return None;
    }
    let mut vals = Vec::with_capacity(top - lo + 1);
    for lag in lo..=top {
        let mut acc = 0.0f32;
        for i in 0..x.len() - lag {
            acc += x[i] * x[i + lag];
        }
        vals.push(acc / e0);
    }
    let mut best = 0usize;
    let mut bv = f32::NEG_INFINITY;
    for (i, v) in vals.iter().enumerate() {
        if *v > bv {
            bv = *v;
            best = i;
        }
    }
    if best == 0 || best + 1 >= vals.len() {
        return None;
    }
    let y0 = vals[best - 1];
    let y1 = vals[best];
    let y2 = vals[best + 1];
    let denom = y0 - 2.0 * y1 + y2;
    let shift = if denom.abs() > 1e-3 * y1.abs() {
        0.5 * (y0 - y2) / denom
    } else {
        0.0
    };
    let lag = lo as f32 + best as f32 + shift.clamp(-1.0, 1.0);
    Some(SR as f32 / lag)
}

fn k1_phase(frame: &[f32], f0_guess: f32) -> f32 {
    use rustfft::num_complex::Complex;
    use rustfft::FftPlanner;
    let n = 16384usize;
    let mut buf = vec![Complex::new(0.0f32, 0.0); n];
    let m = frame.len() as f32;
    for (i, s) in frame.iter().enumerate() {
        let w = 0.5 - 0.5 * (std::f32::consts::PI * 2.0 * i as f32 / m).cos();
        buf[i] = Complex::new(s * w, 0.0);
    }
    FftPlanner::new().plan_fft_forward(n).process(&mut buf);
    let bin_w = SR as f32 / n as f32;
    let best = (f0_guess / bin_w).round() as usize;
    buf[best.min(n / 2 - 1)].arg()
}

fn wrap_pi(v: f32) -> f32 {
    let t = (v + std::f32::consts::PI) % (2.0 * std::f32::consts::PI);
    let t = if t < 0.0 {
        t + 2.0 * std::f32::consts::PI
    } else {
        t
    };
    t - std::f32::consts::PI
}

fn circular_std(resids: &[f32]) -> f32 {
    let n = resids.len() as f32;
    let (sx, cy) = resids
        .iter()
        .fold((0.0f32, 0.0f32), |(sx, cy), r| (sx + r.sin(), cy + r.cos()));
    let r = ((sx / n).powi(2) + (cy / n).powi(2)).sqrt().min(1.0);
    if r <= 1e-9 {
        return f32::INFINITY;
    }
    (-2.0 * r.ln()).sqrt()
}

fn render_solo() -> Vec<f32> {
    let out = articul_cli::render_sentence("a:a:", SR, 120.0);
    assert!(out.len() > REG_B);
    out
}

#[test]
fn jitter_in_natural_band() {
    let dur = 5844.0 / SR as f32;
    let full = flat_source().generate(dur, SR);
    assert!(full.len() > REG_B);
    let region = &full[REG_A..REG_B];
    let periods = corr_periods(region);
    assert!(
        periods.len() >= 10,
        "need >=10 periods, got {}",
        periods.len()
    );
    let j = local_jitter(&periods);
    assert!(
        (0.005..=0.010).contains(&j),
        "local jitter {j:.4} outside natural band 0.5-1.0%"
    );
}

#[test]
fn pulse_shape_varies() {
    let dur = 5844.0 / SR as f32;
    let full = voiced_source().generate(dur, SR);
    assert!(full.len() > REG_B);
    let region = &full[REG_A..REG_B];
    let mut starts = Vec::new();
    let mut s = 0usize;
    while s + FRAME_LEN <= region.len() {
        starts.push(s);
        s += FRAME_HOP;
    }
    assert!(starts.len() >= 5, "need >=5 frames, got {}", starts.len());
    let mut f0s = Vec::with_capacity(starts.len());
    let mut phases = Vec::with_capacity(starts.len());
    let mut guess = None;
    for st in &starts {
        let frame = &region[*st..*st + FRAME_LEN];
        let f0 = autocorr_f0_tracked(frame, guess)
            .or_else(|| autocorr_f0(frame))
            .expect("voiced frame must yield f0");
        guess = Some(f0);
        phases.push(k1_phase(frame, f0));
        f0s.push(f0);
    }
    let mut resids = Vec::with_capacity(phases.len() - 1);
    for j in 1..phases.len() {
        let fb = 0.5 * (f0s[j - 1] + f0s[j]);
        let pred = 2.0 * std::f32::consts::PI * fb * FRAME_HOP as f32 / SR as f32;
        resids.push(wrap_pi(phases[j] - phases[j - 1] - pred));
    }
    let r = circular_std(&resids);
    assert!(
        r > 0.14,
        "k1 phase residual {r:.3} rad must be clearly above the 0.12 rad locked-pulse floor"
    );
}

#[test]
fn microtremor_present() {
    let out = render_solo();
    let mut starts = Vec::new();
    let mut s = REG_A;
    while s + WIN_LEN <= REG_B {
        starts.push(s);
        s += WIN_HOP;
    }
    assert!(
        starts.len() >= 20,
        "need >=20 windows, got {}",
        starts.len()
    );
    let mut f0s = Vec::with_capacity(starts.len());
    let mut guess = None;
    for st in &starts {
        let win = &out[*st..*st + WIN_LEN];
        let f0 = autocorr_f0_tracked(win, guess)
            .or_else(|| autocorr_f0(win))
            .expect("voiced window must yield f0");
        guess = Some(f0);
        f0s.push(f0);
    }
    let n = f0s.len() as f32;
    let cx: f32 = (0..f0s.len()).map(|i| i as f32).sum::<f32>() / n;
    let cy: f32 = f0s.iter().sum::<f32>() / n;
    let sxx: f32 = (0..f0s.len()).map(|i| (i as f32 - cx).powi(2)).sum();
    let sxy: f32 = (0..f0s.len())
        .map(|i| (i as f32 - cx) * (f0s[i] - cy))
        .sum();
    let slope = if sxx > 1e-9 { sxy / sxx } else { 0.0 };
    let detrended: Vec<f32> = (0..f0s.len())
        .map(|i| f0s[i] - slope * (i as f32 - cx))
        .collect();
    let mean = detrended.iter().sum::<f32>() / n;
    let var = detrended.iter().map(|v| (v - mean).powi(2)).sum::<f32>() / n;
    let rel = var.sqrt() / mean;
    assert!(
        rel >= 0.004,
        "detrended sub-syllabic F0 std {rel:.4} must reach the 0.4% tremor floor"
    );
}
