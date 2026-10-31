use crate::cascade::Resonator;

#[derive(Debug, Clone)]
pub struct ParallelFilter {
    branches: Vec<(Resonator, f32)>,
}

impl ParallelFilter {
    pub fn from_pairs(pairs: &[(f32, f32, f32)], sample_rate: u32) -> Self {
        Self {
            branches: pairs
                .iter()
                .map(|(f, b, a)| (Resonator::new(*f, *b, sample_rate), *a))
                .collect(),
        }
    }

    pub fn process(&self, input: &[f32]) -> Vec<f32> {
        let mut branches = self.branches.clone();
        let mut out = vec![0.0; input.len()];
        for (i, x) in input.iter().enumerate() {
            let mut acc = 0.0;
            for (r, amp) in branches.iter_mut() {
                acc += r.step(*x) * *amp;
            }
            out[i] = acc;
        }
        out
    }

    pub fn step(&mut self, x: f32) -> f32 {
        let mut acc = 0.0;
        for (r, amp) in self.branches.iter_mut() {
            acc += r.step(x) * *amp;
        }
        acc
    }

    pub fn retune(&mut self, triples: &[(f32, f32, f32)], sample_rate: u32) {
        if triples.len() == self.branches.len() {
            for ((f, b, a), (r, amp)) in triples.iter().zip(self.branches.iter_mut()) {
                r.retune(*f, *b, sample_rate);
                *amp = *a;
            }
        } else {
            self.branches = triples
                .iter()
                .map(|(f, b, a)| (Resonator::new(*f, *b, sample_rate), *a))
                .collect();
        }
    }
}

pub fn nasal_notch(phoneme: &articul_phon::Phoneme) -> Option<(f32, f32)> {
    let nasal = phoneme.is_nasal() || phoneme.secondary.nasalized;
    if nasal {
        Some((1000.0, 150.0))
    } else {
        None
    }
}

pub fn lateral_notch(phoneme: &articul_phon::Phoneme) -> Option<(f32, f32)> {
    let lateral = matches!(
        phoneme.manner(),
        Some(articul_phon::Manner::LateralApproximant)
    );
    if lateral {
        Some((2500.0, 300.0))
    } else {
        None
    }
}

pub fn frication_noise(len: usize, level: f32) -> Vec<f32> {
    let mut rng = 0x9E3779B9u32;
    let mut out = Vec::with_capacity(len);
    for _ in 0..len {
        rng = rng.wrapping_mul(1664525).wrapping_add(1013904223);
        let uniform = ((rng >> 8) as f32) / 16777216.0 * 2.0 - 1.0;
        out.push((uniform * level).clamp(-1.0, 1.0));
    }
    out
}

pub fn nasalize_bandwidths(bandwidths: &[f32]) -> Vec<f32> {
    bandwidths.iter().map(|b| b * 1.5).collect()
}

pub fn fricative_shaping(phoneme: &articul_phon::Phoneme) -> Vec<(f32, f32, f32)> {
    use articul_phon::Manner;
    use articul_phon::Place;
    let sibilant = matches!(
        (phoneme.manner(), phoneme.place()),
        (
            Some(Manner::Fricative),
            Some(Place::Alveolar | Place::Postalveolar | Place::Retroflex)
        )
    );
    let postalveolar = matches!(
        (phoneme.manner(), phoneme.place()),
        (Some(Manner::Fricative), Some(Place::Postalveolar))
    );
    let lateral = matches!(phoneme.manner(), Some(Manner::LateralFricative));
    if lateral {
        vec![(4200.0, 800.0, 0.8)]
    } else if postalveolar {
        vec![(2800.0, 500.0, 1.0), (5200.0, 900.0, 0.5)]
    } else if sibilant {
        vec![(5200.0, 600.0, 1.0), (7000.0, 1000.0, 0.5)]
    } else {
        vec![(1400.0, 400.0, 0.4), (2600.0, 600.0, 0.25)]
    }
}

pub fn nasal_branch_needed(phoneme: &articul_phon::Phoneme) -> bool {
    phoneme.is_nasal()
}

pub fn frication_level_for(phoneme: &articul_phon::Phoneme, base: f32) -> f32 {
    let boosted = match phoneme.manner() {
        Some(articul_phon::Manner::Fricative) | Some(articul_phon::Manner::LateralFricative) => {
            !phoneme.is_voiced()
        }
        _ => false,
    };
    if boosted {
        (base + 0.4).min(1.0)
    } else {
        base
    }
}
