use dasp::frame::Mono;

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct GlottalSource {
    pub f0_hz: f32,
    pub open_quotient: f32,
    pub asymmetry: f32,
    pub aspiration_noise: f32,
}

const JITTER_DEPTH: f32 = 0.008;
const SHIMMER_DEPTH: f32 = 0.03;
const CYCLE_WHITE_DEPTH: f32 = 0.005;
const CYCLE_SLOW_DEPTH: f32 = 0.006;
const CYCLE_SLOW_LP: f32 = 0.90;
const CYCLE_TREMOR_RATE: f32 = 3.1;
const CYCLE_TREMOR_DEPTH: f32 = 0.004;
const SHAPE_OQ_DEPTH: f32 = 0.7;
const SHAPE_OQ_LP: f32 = 0.95;
const SHAPE_ASYM_DEPTH: f32 = 0.5;
const SHAPE_ASYM_LP: f32 = 0.95;
const MICROTREMOR_RATE: f32 = 2.5;
const MICROTREMOR_DEPTH: f32 = 0.009;

fn lcg11(rng: &mut u32) -> f32 {
    *rng = rng.wrapping_mul(1664525).wrapping_add(1013904223);
    ((*rng >> 8) as f32) / 16777216.0 * 2.0 - 1.0
}

struct CycleState {
    rng: u32,
    slow_j: f32,
    slow_oq: f32,
    slow_as: f32,
    cyc_jit: f64,
    oq: f64,
    asym: f64,
    trem_ph: f32,
    mt_ph: f32,
}

impl CycleState {
    fn fresh(base_oq: f64, base_asym: f64) -> Self {
        let mut rng = 0x9e3779b9u32;
        let trem_ph = lcg11(&mut rng) * std::f32::consts::PI;
        let mt_ph = lcg11(&mut rng) * std::f32::consts::PI;
        CycleState {
            rng,
            slow_j: 0.0,
            slow_oq: 0.0,
            slow_as: 0.0,
            cyc_jit: 1.0,
            oq: base_oq,
            asym: base_asym,
            trem_ph,
            mt_ph,
        }
    }
    fn on_cycle(&mut self, t: f64, base_oq: f64, base_asym: f64) {
        let w = lcg11(&mut self.rng);
        self.slow_j = CYCLE_SLOW_LP * self.slow_j + (1.0 - CYCLE_SLOW_LP) * w;
        let w2 = lcg11(&mut self.rng);
        self.slow_oq = SHAPE_OQ_LP * self.slow_oq + (1.0 - SHAPE_OQ_LP) * w2;
        let w3 = lcg11(&mut self.rng);
        self.slow_as = SHAPE_ASYM_LP * self.slow_as + (1.0 - SHAPE_ASYM_LP) * w3;
        let trem =
            (2.0 * std::f64::consts::PI * CYCLE_TREMOR_RATE as f64 * t + self.trem_ph as f64).sin();
        self.cyc_jit = 1.0
            + CYCLE_WHITE_DEPTH as f64 * w as f64
            + CYCLE_SLOW_DEPTH as f64 * self.slow_j as f64
            + CYCLE_TREMOR_DEPTH as f64 * trem;
        self.oq = (base_oq * (1.0 + SHAPE_OQ_DEPTH as f64 * self.slow_oq as f64)).clamp(0.05, 0.95);
        self.asym = (base_asym + SHAPE_ASYM_DEPTH as f64 * self.slow_as as f64).clamp(0.05, 0.95);
    }
    fn micro(&self, t: f64) -> f64 {
        1.0 + MICROTREMOR_DEPTH as f64
            * (2.0 * std::f64::consts::PI * MICROTREMOR_RATE as f64 * t + self.mt_ph as f64).sin()
    }
}

fn pulse_peak(pulse: &[f32]) -> f32 {
    pulse
        .iter()
        .map(|v| v.abs())
        .fold(0.0f32, f32::max)
        .max(1e-9)
}

impl GlottalSource {
    pub fn generate(&self, duration_secs: f32, sample_rate: u32) -> Vec<f32> {
        let n = (duration_secs * sample_rate as f32).round().max(1.0) as usize;
        if self.f0_hz.is_nan() || self.f0_hz <= 0.0 || sample_rate == 0 {
            return vec![0.0; n];
        }
        let mut pulse = lf_pulse(self, sample_rate);
        let mut peak = pulse_peak(&pulse);
        let period = pulse.len() as f64;
        let mut out = Vec::with_capacity(n);
        let mut rng = 0x12345678u32;
        let mut cyc = CycleState::fresh(self.open_quotient as f64, self.asymmetry as f64);
        let mut phase = 0.0f64;
        let mut shim = 1.0f32;
        let mut prev_cyc = 0.0f64;
        for i in 0..n {
            let t = i as f64 / sample_rate as f64;
            let jit = 1.0 + JITTER_DEPTH as f64 * lcg11(&mut rng) as f64;
            phase += self.f0_hz as f64 * jit * cyc.cyc_jit * cyc.micro(t) / sample_rate as f64;
            let cyc_now = phase % 1.0;
            if cyc_now < prev_cyc {
                shim = 1.0 + SHIMMER_DEPTH * lcg11(&mut rng);
                cyc.on_cycle(t, self.open_quotient as f64, self.asymmetry as f64);
                pulse = lf_pulse_params(self.f0_hz as f64, cyc.oq, cyc.asym, sample_rate);
                peak = pulse_peak(&pulse);
            }
            prev_cyc = cyc_now;
            let pos = cyc_now * period;
            let i0 = pos as usize % pulse.len();
            let i1 = (i0 + 1) % pulse.len();
            let frac = (pos - pos.floor()) as f32;
            let v = pulse[i0] * (1.0 - frac) + pulse[i1] * frac;
            let flow = (v / peak).clamp(0.0, 1.0);
            let uniform = lcg11(&mut rng);
            let s = v / peak * shim + uniform * self.aspiration_noise * 0.5 * (0.3 + 0.7 * flow);
            out.push(s.clamp(-1.0, 1.0));
        }
        out
    }

    pub fn generate_cf0_onset(&self, duration_secs: f32, sample_rate: u32) -> Vec<f32> {
        let n = (duration_secs * sample_rate as f32).round().max(1.0) as usize;
        if self.f0_hz.is_nan() || self.f0_hz <= 0.0 || sample_rate == 0 {
            return vec![0.0; n];
        }
        let mut pulse = lf_pulse(self, sample_rate);
        let mut peak = pulse_peak(&pulse);
        let period = pulse.len() as f64;
        let mut out = Vec::with_capacity(n);
        let mut rng = 0x12345678u32;
        let mut cyc = CycleState::fresh(self.open_quotient as f64, self.asymmetry as f64);
        let mut phase = 0.0f64;
        let mut shim = 1.0f32;
        let mut prev_cyc = 0.0f64;
        for i in 0..n {
            let t = i as f32 / sample_rate as f32;
            let tt = t as f64;
            let f = self.f0_hz as f64 * cf0_boost_factor(t) as f64;
            let jit = 1.0 + JITTER_DEPTH as f64 * lcg11(&mut rng) as f64;
            phase += f * jit * cyc.cyc_jit * cyc.micro(tt) / sample_rate as f64;
            let cyc_now = phase % 1.0;
            if cyc_now < prev_cyc {
                shim = 1.0 + SHIMMER_DEPTH * lcg11(&mut rng);
                cyc.on_cycle(tt, self.open_quotient as f64, self.asymmetry as f64);
                pulse = lf_pulse_params(self.f0_hz as f64, cyc.oq, cyc.asym, sample_rate);
                peak = pulse_peak(&pulse);
            }
            prev_cyc = cyc_now;
            let pos = cyc_now * period;
            let i0 = pos as usize % pulse.len();
            let i1 = (i0 + 1) % pulse.len();
            let frac = (pos - pos.floor()) as f32;
            let v = pulse[i0] * (1.0 - frac) + pulse[i1] * frac;
            let flow = (v / peak).clamp(0.0, 1.0);
            let uniform = lcg11(&mut rng);
            let s = v / peak * shim + uniform * self.aspiration_noise * 0.5 * (0.3 + 0.7 * flow);
            out.push(s.clamp(-1.0, 1.0));
        }
        out
    }

    pub fn generate_glide(&self, duration_secs: f32, sample_rate: u32, f0_end_hz: f32) -> Vec<f32> {
        let n = (duration_secs * sample_rate as f32).round().max(1.0) as usize;
        if self.f0_hz.is_nan()
            || self.f0_hz <= 0.0
            || f0_end_hz.is_nan()
            || f0_end_hz <= 0.0
            || sample_rate == 0
        {
            return vec![0.0; n];
        }
        let mut pulse = lf_pulse(self, sample_rate);
        let mut peak = pulse_peak(&pulse);
        let period = pulse.len() as f64;
        let mut out = Vec::with_capacity(n);
        let mut rng = 0x12345678u32;
        let mut cyc = CycleState::fresh(self.open_quotient as f64, self.asymmetry as f64);
        let mut phase = 0.0f64;
        let mut shim = 1.0f32;
        let mut prev_cyc = 0.0f64;
        let span = n.max(2) as f64 - 1.0;
        for i in 0..n {
            let t = i as f64 / span;
            let ts = i as f64 / sample_rate as f64;
            let w = 0.5 - 0.5 * (std::f64::consts::PI * t).cos();
            let f = self.f0_hz as f64 + (f0_end_hz as f64 - self.f0_hz as f64) * w;
            let jit = 1.0 + JITTER_DEPTH as f64 * lcg11(&mut rng) as f64;
            phase += f * jit * cyc.cyc_jit * cyc.micro(ts) / sample_rate as f64;
            let cyc_now = phase % 1.0;
            if cyc_now < prev_cyc {
                shim = 1.0 + SHIMMER_DEPTH * lcg11(&mut rng);
                cyc.on_cycle(ts, self.open_quotient as f64, self.asymmetry as f64);
                pulse = lf_pulse_params(self.f0_hz as f64, cyc.oq, cyc.asym, sample_rate);
                peak = pulse_peak(&pulse);
            }
            prev_cyc = cyc_now;
            let pos = cyc_now * period;
            let i0 = pos as usize % pulse.len();
            let i1 = (i0 + 1) % pulse.len();
            let frac = (pos - pos.floor()) as f32;
            let v = pulse[i0] * (1.0 - frac) + pulse[i1] * frac;
            let flow = (v / peak).clamp(0.0, 1.0);
            let uniform = lcg11(&mut rng);
            let s = v / peak * shim + uniform * self.aspiration_noise * 0.5 * (0.3 + 0.7 * flow);
            out.push(s.clamp(-1.0, 1.0));
        }
        out
    }

    pub fn generate_exp_glide(
        &self,
        duration_secs: f32,
        sample_rate: u32,
        f0_end_hz: f32,
    ) -> Vec<f32> {
        let n = (duration_secs * sample_rate as f32).round().max(1.0) as usize;
        if self.f0_hz.is_nan()
            || self.f0_hz <= 0.0
            || f0_end_hz.is_nan()
            || f0_end_hz <= 0.0
            || sample_rate == 0
        {
            return vec![0.0; n];
        }
        let mut pulse = lf_pulse(self, sample_rate);
        let mut peak = pulse_peak(&pulse);
        let period = pulse.len() as f64;
        let mut out = Vec::with_capacity(n);
        let mut rng = 0x12345678u32;
        let mut cyc = CycleState::fresh(self.open_quotient as f64, self.asymmetry as f64);
        let mut phase = 0.0f64;
        let mut shim = 1.0f32;
        let mut prev_cyc = 0.0f64;
        let tau = (duration_secs as f64 / 4.0).max(1e-6);
        for i in 0..n {
            let t = i as f64 / sample_rate as f64;
            let f = f0_end_hz as f64 + (self.f0_hz as f64 - f0_end_hz as f64) * (-t / tau).exp();
            let jit = 1.0 + JITTER_DEPTH as f64 * lcg11(&mut rng) as f64;
            phase += f * jit * cyc.cyc_jit * cyc.micro(t) / sample_rate as f64;
            let cyc_now = phase % 1.0;
            if cyc_now < prev_cyc {
                shim = 1.0 + SHIMMER_DEPTH * lcg11(&mut rng);
                cyc.on_cycle(t, self.open_quotient as f64, self.asymmetry as f64);
                pulse = lf_pulse_params(self.f0_hz as f64, cyc.oq, cyc.asym, sample_rate);
                peak = pulse_peak(&pulse);
            }
            prev_cyc = cyc_now;
            let pos = cyc_now * period;
            let i0 = pos as usize % pulse.len();
            let i1 = (i0 + 1) % pulse.len();
            let frac = (pos - pos.floor()) as f32;
            let v = pulse[i0] * (1.0 - frac) + pulse[i1] * frac;
            let flow = (v / peak).clamp(0.0, 1.0);
            let uniform = lcg11(&mut rng);
            let s = v / peak * shim + uniform * self.aspiration_noise * 0.5 * (0.3 + 0.7 * flow);
            out.push(s.clamp(-1.0, 1.0));
        }
        out
    }

    pub fn generate_cf0_exp_glide(
        &self,
        duration_secs: f32,
        sample_rate: u32,
        f0_end_hz: f32,
    ) -> Vec<f32> {
        let n = (duration_secs * sample_rate as f32).round().max(1.0) as usize;
        if self.f0_hz.is_nan()
            || self.f0_hz <= 0.0
            || f0_end_hz.is_nan()
            || f0_end_hz <= 0.0
            || sample_rate == 0
        {
            return vec![0.0; n];
        }
        let mut pulse = lf_pulse(self, sample_rate);
        let mut peak = pulse_peak(&pulse);
        let period = pulse.len() as f64;
        let mut out = Vec::with_capacity(n);
        let mut rng = 0x12345678u32;
        let mut cyc = CycleState::fresh(self.open_quotient as f64, self.asymmetry as f64);
        let mut phase = 0.0f64;
        let mut shim = 1.0f32;
        let mut prev_cyc = 0.0f64;
        let tau = (duration_secs as f64 / 4.0).max(1e-6);
        for i in 0..n {
            let t = i as f32 / sample_rate as f32;
            let tt = t as f64;
            let contour = f0_end_hz as f64
                + (self.f0_hz as f64 - f0_end_hz as f64) * (-(t as f64) / tau).exp();
            let f = contour * cf0_boost_factor(t) as f64;
            let jit = 1.0 + JITTER_DEPTH as f64 * lcg11(&mut rng) as f64;
            phase += f * jit * cyc.cyc_jit * cyc.micro(tt) / sample_rate as f64;
            let cyc_now = phase % 1.0;
            if cyc_now < prev_cyc {
                shim = 1.0 + SHIMMER_DEPTH * lcg11(&mut rng);
                cyc.on_cycle(tt, self.open_quotient as f64, self.asymmetry as f64);
                pulse = lf_pulse_params(self.f0_hz as f64, cyc.oq, cyc.asym, sample_rate);
                peak = pulse_peak(&pulse);
            }
            prev_cyc = cyc_now;
            let pos = cyc_now * period;
            let i0 = pos as usize % pulse.len();
            let i1 = (i0 + 1) % pulse.len();
            let frac = (pos - pos.floor()) as f32;
            let v = pulse[i0] * (1.0 - frac) + pulse[i1] * frac;
            let flow = (v / peak).clamp(0.0, 1.0);
            let uniform = lcg11(&mut rng);
            let s = v / peak * shim + uniform * self.aspiration_noise * 0.5 * (0.3 + 0.7 * flow);
            out.push(s.clamp(-1.0, 1.0));
        }
        out
    }

    pub fn generate_cf0_glide(
        &self,
        duration_secs: f32,
        sample_rate: u32,
        f0_end_hz: f32,
    ) -> Vec<f32> {
        let n = (duration_secs * sample_rate as f32).round().max(1.0) as usize;
        if self.f0_hz.is_nan()
            || self.f0_hz <= 0.0
            || f0_end_hz.is_nan()
            || f0_end_hz <= 0.0
            || sample_rate == 0
        {
            return vec![0.0; n];
        }
        let mut pulse = lf_pulse(self, sample_rate);
        let mut peak = pulse_peak(&pulse);
        let period = pulse.len() as f64;
        let mut out = Vec::with_capacity(n);
        let mut rng = 0x12345678u32;
        let mut cyc = CycleState::fresh(self.open_quotient as f64, self.asymmetry as f64);
        let mut phase = 0.0f64;
        let mut shim = 1.0f32;
        let mut prev_cyc = 0.0f64;
        let span = n.max(2) as f64 - 1.0;
        for i in 0..n {
            let t = i as f32 / sample_rate as f32;
            let tt = t as f64;
            let g = i as f64 / span;
            let w = 0.5 - 0.5 * (std::f64::consts::PI * g).cos();
            let base = self.f0_hz as f64 + (f0_end_hz as f64 - self.f0_hz as f64) * w;
            let f = base * cf0_boost_factor(t) as f64;
            let jit = 1.0 + JITTER_DEPTH as f64 * lcg11(&mut rng) as f64;
            phase += f * jit * cyc.cyc_jit * cyc.micro(tt) / sample_rate as f64;
            let cyc_now = phase % 1.0;
            if cyc_now < prev_cyc {
                shim = 1.0 + SHIMMER_DEPTH * lcg11(&mut rng);
                cyc.on_cycle(tt, self.open_quotient as f64, self.asymmetry as f64);
                pulse = lf_pulse_params(self.f0_hz as f64, cyc.oq, cyc.asym, sample_rate);
                peak = pulse_peak(&pulse);
            }
            prev_cyc = cyc_now;
            let pos = cyc_now * period;
            let i0 = pos as usize % pulse.len();
            let i1 = (i0 + 1) % pulse.len();
            let frac = (pos - pos.floor()) as f32;
            let v = pulse[i0] * (1.0 - frac) + pulse[i1] * frac;
            let flow = (v / peak).clamp(0.0, 1.0);
            let uniform = lcg11(&mut rng);
            let s = v / peak * shim + uniform * self.aspiration_noise * 0.5 * (0.3 + 0.7 * flow);
            out.push(s.clamp(-1.0, 1.0));
        }
        out
    }

    pub fn generate_creak(&self, duration_secs: f32, sample_rate: u32) -> Vec<f32> {
        let n = (duration_secs * sample_rate as f32).round().max(1.0) as usize;
        if self.f0_hz.is_nan() || self.f0_hz <= 0.0 || sample_rate == 0 {
            return vec![0.0; n];
        }
        let pulse = lf_pulse(self, sample_rate);
        let peak = pulse
            .iter()
            .map(|v| v.abs())
            .fold(0.0f32, f32::max)
            .max(1e-9);
        let period = pulse.len() as f64;
        let mut out = Vec::with_capacity(n);
        let mut rng = 0x12345678u32;
        let mut phase = 0.0f64;
        let mut prev_cyc = 0.0f64;
        let mut k = 0usize;
        for i in 0..n {
            let frac = (i as f64 / n.max(2) as f64).min(1.0);
            let depth = ((frac - 0.4) / 0.6).clamp(0.0, 1.0);
            let cyc = phase % 1.0;
            if cyc < prev_cyc {
                k += 1;
            }
            prev_cyc = cyc;
            let mult = if k % 2 == 1 {
                1.0 / (1.0 + 0.6 * depth)
            } else {
                1.0
            };
            let amp = if k % 2 == 1 {
                (1.0 - 0.4 * depth) as f32
            } else {
                1.0
            };
            phase += self.f0_hz as f64 * mult / sample_rate as f64;
            let pos = ((phase % 1.0) * period) as usize % pulse.len().max(1);
            let v = pulse[pos] * amp;
            let flow = (v / peak).clamp(0.0, 1.0);
            let uniform = lcg11(&mut rng);
            let s = v / peak + uniform * self.aspiration_noise * 0.5 * (0.3 + 0.7 * flow);
            out.push(s.clamp(-1.0, 1.0));
        }
        out
    }

    pub fn to_mono_frames(samples: &[f32]) -> Vec<Mono<f32>> {
        samples.iter().map(|s| [*s]).collect()
    }
}

pub fn cf0_boost_factor(t_secs: f32) -> f32 {
    if t_secs <= 0.04 {
        1.10
    } else {
        1.0 + 0.10 * (-(t_secs - 0.04) / 0.02).exp()
    }
}

pub fn lf_pulse_shape(
    f0_hz: f64,
    open_quotient: f64,
    asymmetry: f64,
    sample_rate: u32,
) -> Vec<f32> {
    lf_pulse_params(f0_hz, open_quotient, asymmetry, sample_rate)
}

fn lf_pulse(src: &GlottalSource, sample_rate: u32) -> Vec<f32> {
    lf_pulse_params(
        src.f0_hz as f64,
        src.open_quotient as f64,
        src.asymmetry as f64,
        sample_rate,
    )
}

fn lf_pulse_params(f0: f64, oq_in: f64, asym_in: f64, sample_rate: u32) -> Vec<f32> {
    let t0 = 1.0 / f0;
    let oq = oq_in.clamp(0.05, 0.95);
    let asym = asym_in.clamp(0.0, 1.0);
    let te = oq * t0;
    let mut tp = te * (0.82 - 0.10 * asym);
    let tp_min = te / 1.9;
    if tp < tp_min {
        tp = tp_min;
    }
    let ta = t0 * (0.015 + 0.015 * asym);
    let tc = t0;
    let wg = std::f64::consts::PI / tp;
    let eps = 1.0 / ta;
    let alpha = solve_alpha(te, ta, tc, wg, eps);
    let sw = (wg * te).sin();
    let e_tc = (-eps * (tc - te)).exp();
    let c0 = (1.0 - e_tc) / (eps * ta);
    let e0 = -c0 / ((alpha * te).exp() * sw);
    let dt = 1.0 / sample_rate as f64;
    let m = ((tc / dt).round() as usize).max(1);
    let mut out = Vec::with_capacity(m);
    let mut flow = 0.0;
    for i in 0..m {
        let t = i as f64 * dt;
        let e = if t < te {
            e0 * (alpha * t).exp() * (wg * t).sin()
        } else if t < tc {
            -(((-eps * (t - te)).exp() - e_tc) / (eps * ta))
        } else {
            0.0
        };
        flow += e * dt;
        out.push(flow as f32);
    }
    out
}

fn lf_total(alpha: f64, te: f64, wg: f64, eps: f64, ta: f64, tc: f64) -> f64 {
    let sw = (wg * te).sin();
    let cw = (wg * te).cos();
    let d = (alpha * te).exp() * sw;
    if d == 0.0 {
        return f64::NAN;
    }
    let j = ((alpha * te).exp() * (alpha * sw - wg * cw) + wg) / (alpha * alpha + wg * wg);
    let e_tc = (-eps * (tc - te)).exp();
    let k = -(1.0 / (eps * ta)) * ((1.0 - e_tc) / eps - e_tc * (tc - te));
    let c0 = (1.0 - e_tc) / (eps * ta);
    -c0 * j / d + k
}

fn solve_alpha(te: f64, ta: f64, tc: f64, wg: f64, eps: f64) -> f64 {
    let g = |a: f64| lf_total(a, te, wg, eps, ta, tc);
    let g0 = g(0.0);
    let (mut lo, mut hi) = if g0 > 0.0 {
        let mut hi = 500.0;
        loop {
            let v = g(hi);
            if v < 0.0 || !v.is_finite() || hi >= 1e9 {
                break;
            }
            hi *= 2.0;
        }
        (0.0, hi)
    } else {
        let mut lo = -500.0;
        loop {
            let v = g(lo);
            if v > 0.0 || !v.is_finite() || lo <= -1e9 {
                break;
            }
            lo *= 2.0;
        }
        (lo, 0.0)
    };
    let mut best = (lo + hi) * 0.5;
    let mut best_v = g(best).abs();
    for _ in 0..80 {
        let mid = (lo + hi) * 0.5;
        let v = g(mid);
        if v.abs() < best_v {
            best = mid;
            best_v = v.abs();
        }
        if (v > 0.0) == (g(lo) > 0.0) {
            lo = mid;
        } else {
            hi = mid;
        }
        if !v.is_finite() {
            break;
        }
    }
    best
}

pub fn effective_aspiration(phoneme: &articul_phon::Phoneme, base_noise: f32) -> f32 {
    if phoneme.secondary.aspirated {
        (base_noise + 0.3).min(1.0)
    } else {
        base_noise
    }
}
