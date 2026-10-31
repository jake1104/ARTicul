#[derive(Debug, Clone, Copy)]
pub struct Resonator {
    a: f32,
    b: f32,
    c: f32,
    y1: f32,
    y2: f32,
}

impl Resonator {
    pub fn new(freq_hz: f32, bw_hz: f32, sample_rate: u32) -> Self {
        let t = 1.0 / sample_rate as f32;
        let c = (-2.0 * std::f32::consts::PI * bw_hz * t).exp();
        let c = -c;
        let b = 2.0
            * (-std::f32::consts::PI * bw_hz * t).exp()
            * (2.0 * std::f32::consts::PI * freq_hz * t).cos();
        let a = 1.0 - b - c;
        Self {
            a,
            b,
            c,
            y1: 0.0,
            y2: 0.0,
        }
    }

    pub fn step(&mut self, x: f32) -> f32 {
        let y = self.a * x + self.b * self.y1 + self.c * self.y2;
        self.y2 = self.y1;
        self.y1 = y;
        y
    }

    pub fn retune(&mut self, freq_hz: f32, bw_hz: f32, sample_rate: u32) {
        let t = 1.0 / sample_rate as f32;
        let c = (-2.0 * std::f32::consts::PI * bw_hz * t).exp();
        let c = -c;
        let b = 2.0
            * (-std::f32::consts::PI * bw_hz * t).exp()
            * (2.0 * std::f32::consts::PI * freq_hz * t).cos();
        self.a = 1.0 - b - c;
        self.b = b;
        self.c = c;
    }
}

#[derive(Debug, Clone)]
pub struct CascadeFilter {
    stages: Vec<Resonator>,
}

#[derive(Debug, Clone)]
pub struct NotchFilter {
    b0: f32,
    b1: f32,
    b2: f32,
    a1: f32,
    a2: f32,
    x1: f32,
    x2: f32,
    y1: f32,
    y2: f32,
}

impl NotchFilter {
    pub fn new(freq_hz: f32, bw_hz: f32, sample_rate: u32) -> Self {
        let w0 = 2.0 * std::f32::consts::PI * freq_hz / sample_rate as f32;
        let alpha = (w0.sin() * bw_hz / freq_hz / 2.0).max(1e-6);
        let cw = w0.cos();
        let a0 = 1.0 + alpha;
        Self {
            b0: 1.0 / a0,
            b1: -2.0 * cw / a0,
            b2: 1.0 / a0,
            a1: -2.0 * cw / a0,
            a2: (1.0 - alpha) / a0,
            x1: 0.0,
            x2: 0.0,
            y1: 0.0,
            y2: 0.0,
        }
    }

    pub fn step(&mut self, x: f32) -> f32 {
        let y = self.b0 * x + self.b1 * self.x1 + self.b2 * self.x2
            - self.a1 * self.y1
            - self.a2 * self.y2;
        self.x2 = self.x1;
        self.x1 = x;
        self.y2 = self.y1;
        self.y1 = y;
        y
    }

    pub fn process(&mut self, input: &[f32]) -> Vec<f32> {
        input.iter().map(|x| self.step(*x)).collect()
    }
}

impl CascadeFilter {
    pub fn single(freq_hz: f32, bw_hz: f32, sample_rate: u32) -> Self {
        Self {
            stages: vec![Resonator::new(freq_hz, bw_hz, sample_rate)],
        }
    }

    pub fn from_pairs(pairs: &[(f32, f32)], sample_rate: u32) -> Self {
        Self {
            stages: pairs
                .iter()
                .map(|(f, b)| Resonator::new(*f, *b, sample_rate))
                .collect(),
        }
    }

    pub fn process(&self, input: &[f32]) -> Vec<f32> {
        let mut stages = self.stages.clone();
        let mut out = Vec::with_capacity(input.len());
        for x in input {
            let mut v = *x;
            for s in stages.iter_mut() {
                v = s.step(v);
            }
            out.push(v);
        }
        out
    }

    pub fn step(&mut self, x: f32) -> f32 {
        let mut v = x;
        for s in self.stages.iter_mut() {
            v = s.step(v);
        }
        v
    }

    pub fn retune(&mut self, pairs: &[(f32, f32)], sample_rate: u32) {
        let mut fresh: Vec<Resonator> = pairs
            .iter()
            .map(|(f, b)| Resonator::new(*f, *b, sample_rate))
            .collect();
        for (new, old) in fresh.drain(..).zip(self.stages.iter_mut()) {
            let (y1, y2) = (old.y1, old.y2);
            *old = new;
            old.y1 = y1;
            old.y2 = y2;
        }
    }
}
