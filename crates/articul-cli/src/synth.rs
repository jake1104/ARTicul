use articul_dsp::apply_radiation;
use articul_dsp::effective_aspiration;
use articul_dsp::frication_level_for;
use articul_dsp::frication_noise;
use articul_dsp::fricative_shaping;
use articul_dsp::korean_locus_pull;
use articul_dsp::korean_vowel_formants;
use articul_dsp::lateral_notch;
use articul_dsp::locus_pull_toward;
use articul_dsp::nasal_notch;
use articul_dsp::nasalize_bandwidths;
use articul_dsp::reduced_vowel_targets;
use articul_dsp::vowel_formants;
use articul_dsp::CascadeFilter;
use articul_dsp::GlottalSource;
use articul_dsp::NotchFilter;
use articul_dsp::ParallelFilter;
use articul_front::prosody::ProsodicPhoneme;
use articul_front::Stress;
use articul_phon::Manner;
use articul_phon::Phoneme;
use articul_phon::Place;
use articul_phon::SegmentKind;

#[derive(Clone)]
enum FilterSpec {
    Cascade(Vec<(f32, f32)>),
    Parallel(Vec<(f32, f32, f32)>),
}

fn unit_pairs(phoneme: &Phoneme, full: &[(f32, f32)], upper: &[(f32, f32); 3]) -> Vec<(f32, f32)> {
    if let Some((f1, f2, f3)) = vowel_formants(phoneme) {
        vec![
            (f1, 80.0),
            (f2, 100.0),
            (f3, 120.0),
            upper[0],
            upper[1],
            upper[2],
        ]
    } else {
        full.to_vec()
    }
}

fn is_h_onset(unit: &ProsodicPhoneme) -> bool {
    !unit.is_pause
        && !unit.phoneme.is_voiced()
        && matches!(unit.phoneme.manner(), Some(Manner::Fricative))
        && matches!(unit.phoneme.place(), Some(Place::Glottal))
}

fn is_lateral_onset(unit: &ProsodicPhoneme) -> bool {
    !unit.is_pause && matches!(unit.phoneme.manner(), Some(Manner::LateralApproximant))
}

fn spec_for(
    unit: &ProsodicPhoneme,
    neighbor: Option<&ProsodicPhoneme>,
    full: &[(f32, f32)],
    upper: &[(f32, f32); 3],
    korean: bool,
) -> FilterSpec {
    if is_h_onset(unit) {
        if let Some(next) = neighbor {
            if is_vowel(&next.phoneme) {
                if korean {
                    if let Some((f1, f2, f3)) = korean_vowel_formants(&next.phoneme)
                        .or_else(|| vowel_formants(&next.phoneme))
                    {
                        return FilterSpec::Cascade(vec![
                            (f1, 80.0),
                            (f2, 100.0),
                            (f3, 120.0),
                            upper[0],
                            upper[1],
                            upper[2],
                        ]);
                    }
                } else {
                    let stressed = !matches!(next.stress, Stress::Unstressed);
                    if let Some((f1, f2, f3)) = reduced_vowel_targets(&next.phoneme, stressed) {
                        return FilterSpec::Cascade(vec![
                            (f1, 80.0),
                            (f2, 100.0),
                            (f3, 120.0),
                            upper[0],
                            upper[1],
                            upper[2],
                        ]);
                    }
                }
            }
        }
    }
    if is_lateral_onset(unit) && !unit.word_final {
        if let Some(next) = neighbor {
            if is_vowel(&next.phoneme) && !matches!(next.stress, Stress::Unstressed) {
                return FilterSpec::Cascade(vec![
                    (300.0, 80.0),
                    (1400.0, 100.0),
                    (2800.0, 120.0),
                    upper[0],
                    upper[1],
                    upper[2],
                ]);
            }
        }
    }
    if matches!(
        unit.phoneme.manner(),
        Some(Manner::Fricative | Manner::LateralFricative)
    ) {
        return FilterSpec::Parallel(fricative_shaping(&unit.phoneme));
    }
    if is_vowel(&unit.phoneme) {
        if korean {
            let (f1, f2, f3) = korean_vowel_formants(&unit.phoneme)
                .or_else(|| vowel_formants(&unit.phoneme))
                .expect("vowel formants");
            let (f1, f2, f3) = match neighbor {
                Some(nb) if lateral_for_unit(nb, Some(unit)).is_none() => {
                    korean_locus_pull(f1, f2, f3, &unit.phoneme, &nb.phoneme)
                }
                _ => (f1, f2, f3),
            };
            return FilterSpec::Cascade(vec![
                (f1, 80.0),
                (f2, 100.0),
                (f3, 120.0),
                upper[0],
                upper[1],
                upper[2],
            ]);
        }
        let stressed = !matches!(unit.stress, Stress::Unstressed);
        if let Some((f1, f2, f3)) = reduced_vowel_targets(&unit.phoneme, stressed) {
            let (f1, f2, f3) = match neighbor {
                Some(nb) if lateral_for_unit(nb, Some(unit)).is_none() => {
                    match nb.phoneme.place() {
                        Some(place) => locus_pull_toward(f1, f2, f3, place),
                        None => (f1, f2, f3),
                    }
                }
                _ => (f1, f2, f3),
            };
            return FilterSpec::Cascade(vec![
                (f1, 80.0),
                (f2, 100.0),
                (f3, 120.0),
                upper[0],
                upper[1],
                upper[2],
            ]);
        }
    }
    let mut pairs = unit_pairs(&unit.phoneme, full, upper);
    if unit.phoneme.is_nasal() || unit.phoneme.secondary.nasalized {
        let wide = nasalize_bandwidths(&pairs.iter().map(|(_, b)| *b).collect::<Vec<_>>());
        for (p, b) in pairs.iter_mut().zip(wide.iter()) {
            p.1 = *b;
        }
    }
    FilterSpec::Cascade(pairs)
}

fn is_goat_onset(unit: &ProsodicPhoneme) -> bool {
    !unit.is_pause
        && !matches!(unit.stress, Stress::Unstressed)
        && unit.phoneme.base_symbol == "o"
        && matches!(unit.phoneme.kind, SegmentKind::Vowel { rounded: true, .. })
}

fn is_goat_offglide(unit: &ProsodicPhoneme) -> bool {
    !unit.is_pause
        && matches!(unit.stress, Stress::Unstressed)
        && unit.phoneme.base_symbol == "\u{028A}"
        && matches!(unit.phoneme.kind, SegmentKind::Vowel { .. })
}

fn is_goat_pair(first: &ProsodicPhoneme, second: &ProsodicPhoneme) -> bool {
    is_goat_onset(first) && is_goat_offglide(second)
}

type FormantPairs = Vec<(f32, f32)>;

fn diphthong_pairs(
    first: &ProsodicPhoneme,
    upper: &[(f32, f32); 3],
) -> (FormantPairs, FormantPairs) {
    let f3 = vowel_formants(&first.phoneme)
        .map(|(_, _, f)| f)
        .unwrap_or(2300.0);
    let start = vec![
        (500.0, 80.0),
        (900.0, 100.0),
        (f3, 120.0),
        upper[0],
        upper[1],
        upper[2],
    ];
    let end = vec![
        (400.0, 80.0),
        (1100.0, 100.0),
        (f3, 120.0),
        upper[0],
        upper[1],
        upper[2],
    ];
    (start, end)
}

fn lerp_pairs(a: &[(f32, f32)], b: &[(f32, f32)], t: f32) -> Vec<(f32, f32)> {
    a.iter()
        .zip(b.iter())
        .map(|((f0, b0), (f1, b1))| (f0 + (f1 - f0) * t, b0 + (b1 - b0) * t))
        .collect()
}

fn lerp_triples(a: &[(f32, f32, f32)], b: &[(f32, f32, f32)], t: f32) -> Vec<(f32, f32, f32)> {
    a.iter()
        .zip(b.iter())
        .map(|((f0, b0, a0), (f1, b1, a1))| {
            (f0 + (f1 - f0) * t, b0 + (b1 - b0) * t, a0 + (a1 - a0) * t)
        })
        .collect()
}

fn can_glide(a: &FilterSpec, b: &FilterSpec) -> bool {
    match (a, b) {
        (FilterSpec::Cascade(x), FilterSpec::Cascade(y)) => x.len() == y.len(),
        (FilterSpec::Parallel(x), FilterSpec::Parallel(y)) => x.len() == y.len(),
        _ => false,
    }
}

fn filter_glide(
    tail: &[f32],
    head: &[f32],
    from: &FilterSpec,
    to: &FilterSpec,
    nasal: Option<(f32, f32)>,
    sr: u32,
) -> Vec<f32> {
    let n = tail.len().min(head.len());
    let mut mix = Vec::with_capacity(n);
    for k in 0..n {
        let t = k as f32 / n.max(1) as f32;
        mix.push((1.0 - t) * tail[k] + t * head[k]);
    }
    let mut out = Vec::with_capacity(n);
    match (from, to) {
        (FilterSpec::Cascade(a), FilterSpec::Cascade(b)) if a.len() == b.len() => {
            let mut f = CascadeFilter::from_pairs(a, sr);
            for x in tail.iter().take(n) {
                f.step(*x);
            }
            for (k, m) in mix.iter().enumerate() {
                let t = k as f32 / n.max(1) as f32;
                f.retune(&lerp_pairs(a, b, t), sr);
                out.push(f.step(*m));
            }
        }
        (FilterSpec::Parallel(a), FilterSpec::Parallel(b)) if a.len() == b.len() => {
            let mut f = ParallelFilter::from_pairs(a, sr);
            for x in tail.iter().take(n) {
                f.step(*x);
            }
            for (k, m) in mix.iter().enumerate() {
                let t = k as f32 / n.max(1) as f32;
                f.retune(&lerp_triples(a, b, t), sr);
                out.push(f.step(*m));
            }
        }
        _ => {
            out.extend_from_slice(&mix);
        }
    }
    if let Some((f0, bw)) = nasal {
        let mut nf = NotchFilter::new(f0, bw, sr);
        for x in tail.iter().take(n) {
            nf.step(*x);
        }
        for o in out.iter_mut() {
            *o = nf.step(*o);
        }
    }
    out
}

pub fn default_pairs() -> Vec<(f32, f32)> {
    vec![
        (500.0, 60.0),
        (1500.0, 90.0),
        (2500.0, 120.0),
        (3300.0, 150.0),
        (4000.0, 200.0),
        (4900.0, 1000.0),
    ]
}

fn upper_three(pairs: &[(f32, f32)]) -> [(f32, f32); 3] {
    let mut upper = [(3300.0, 150.0), (4000.0, 200.0), (4900.0, 1000.0)];
    for (i, p) in pairs.iter().skip(3).take(3).enumerate() {
        upper[i] = *p;
    }
    upper
}

struct SourceParams {
    open_quotient: f32,
    asymmetry: f32,
    aspiration_noise: f32,
}

pub fn segment_gain_db(unit: &ProsodicPhoneme, index: usize, total: usize) -> f32 {
    let mut g: f32 = match &unit.phoneme.kind {
        SegmentKind::Vowel { .. } => match unit.stress {
            Stress::Unstressed => -1.75,
            Stress::Secondary | Stress::Primary => 0.0,
        },
        SegmentKind::Consonant { place, manner } => match manner {
            Manner::Nasal => -4.0,
            Manner::Approximant | Manner::LateralApproximant | Manner::Trill | Manner::TapFlap => {
                -3.5
            }
            Manner::Fricative => {
                let base = if matches!(unit.phoneme.place(), Some(Place::Glottal))
                    && !unit.phoneme.is_voiced()
                {
                    -10.0
                } else {
                    match place {
                        Place::Alveolar | Place::Postalveolar | Place::Retroflex => -2.5,
                        _ => -9.0,
                    }
                };
                if unit.phoneme.is_voiced() {
                    base - 5.0
                } else {
                    base
                }
            }
            Manner::LateralFricative => {
                if unit.phoneme.is_voiced() {
                    -14.0
                } else {
                    -9.0
                }
            }
            _ => 0.0,
        },
    };
    if unit.phoneme.secondary.aspirated {
        g = g.max(-1.5);
    }
    g -= (index.min(12)) as f32 * 0.5;
    if total > 0 && index + 1 == total && !matches!(unit.phoneme.kind, SegmentKind::Vowel { .. }) {
        g -= 2.0;
    }
    g = g.max(-6.0);
    g
}

struct UnitPos {
    index: usize,
    total: usize,
    korean: bool,
}

enum UnitEnvelope {
    None,
    Fricative,
    Burst,
}

fn envelope_kind(phoneme: &Phoneme, frication_path: bool) -> UnitEnvelope {
    if matches!(phoneme.manner(), Some(Manner::Plosive | Manner::Ejective)) && !phoneme.is_voiced()
    {
        UnitEnvelope::Burst
    } else if frication_path {
        UnitEnvelope::Fricative
    } else {
        UnitEnvelope::None
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Cf0Mode {
    None,
    Flat,
    Decay,
}

pub fn cf0_mode(is_vowel: bool, prev_voiceless_obstruent: bool, duration_ms: u32) -> Cf0Mode {
    if !is_vowel || !prev_voiceless_obstruent {
        Cf0Mode::None
    } else if duration_ms < 50 {
        Cf0Mode::Flat
    } else {
        Cf0Mode::Decay
    }
}

fn is_voiceless_obstruent_phoneme(phoneme: &Phoneme) -> bool {
    !phoneme.is_voiced()
        && matches!(
            phoneme.manner(),
            Some(
                Manner::Plosive
                    | Manner::Fricative
                    | Manner::LateralFricative
                    | Manner::Ejective
                    | Manner::FricatedClick
            )
        )
}

fn apply_envelope(samples: &mut [f32], kind: UnitEnvelope, sample_rate: u32) {
    let n = samples.len();
    if n == 0 {
        return;
    }
    match kind {
        UnitEnvelope::None => {}
        UnitEnvelope::Fricative => {
            let atk = ((0.090 * sample_rate as f32) as usize).max(1).min(n);
            let rel = ((0.010 * sample_rate as f32) as usize).min(n.saturating_sub(atk));
            for (i, s) in samples.iter_mut().enumerate() {
                let a = if atk > 1 && i < atk {
                    i as f32 / (atk - 1) as f32
                } else {
                    1.0
                };
                let r = if rel > 0 && i >= n - rel {
                    ((n - 1 - i) as f32 / rel as f32).min(1.0)
                } else {
                    1.0
                };
                *s *= a * r;
            }
        }
        UnitEnvelope::Burst => {
            let atk = ((0.005 * sample_rate as f32) as usize).max(1).min(n);
            for (i, s) in samples.iter_mut().enumerate() {
                let a = if atk > 1 && i < atk {
                    i as f32 / (atk - 1) as f32
                } else {
                    1.0
                };
                let t = i as f32 / sample_rate as f32;
                let t0 = atk as f32 / sample_rate as f32;
                let d = if t <= t0 {
                    1.0
                } else {
                    0.05f32.max((-(t - t0) / 0.015).exp())
                };
                *s *= a * d;
            }
        }
    }
}

const FINAL_FADE_DB: f32 = -12.0;
const FINAL_FADE_MS: f32 = 150.0;

fn apply_final_fade(samples: &mut [f32], sample_rate: u32, final_unit_samples: Option<usize>) {
    let n = samples.len();
    if n == 0 {
        return;
    }
    let cap = ((FINAL_FADE_MS / 1000.0 * sample_rate as f32) as usize).min(n);
    let k = match final_unit_samples {
        Some(m) if m > 0 => cap.min(m),
        _ => cap,
    };
    let floor = 10f32.powf(FINAL_FADE_DB / 20.0);
    let start = n - k;
    for (i, s) in samples.iter_mut().enumerate().skip(start) {
        let t = (i - start) as f32 / k.max(1) as f32;
        let m = floor + (1.0 - floor) * 0.5 * (1.0 + (std::f32::consts::PI * t).cos());
        *s *= m;
    }
}

fn render_unit(
    unit: &ProsodicPhoneme,
    params: &SourceParams,
    filter: &dyn Fn(&[f32]) -> Vec<f32>,
    sample_rate: u32,
    pos: &UnitPos,
    prev: Option<&ProsodicPhoneme>,
) -> (Vec<f32>, Vec<f32>) {
    let n = ((unit.duration_ms as f32 / 1000.0) * sample_rate as f32)
        .round()
        .max(1.0) as usize;
    let frication = frication_level_for(&unit.phoneme, params.aspiration_noise) > 0.1;
    let voiced_mixed = !unit.is_pause
        && unit.phoneme.is_voiced()
        && matches!(
            unit.phoneme.manner(),
            Some(Manner::Fricative | Manner::LateralFricative)
        );
    let raw = if unit.is_pause {
        vec![0.0; n]
    } else if frication {
        frication_noise(n, 0.3)
    } else {
        let cf0 = cf0_mode(
            is_vowel(&unit.phoneme),
            prev.is_some_and(|p| is_voiceless_obstruent_phoneme(&p.phoneme)),
            unit.duration_ms,
        );
        let src = GlottalSource {
            f0_hz: match cf0 {
                Cf0Mode::Flat => unit.f0_hz * 1.05,
                _ => unit.f0_hz,
            },
            open_quotient: params.open_quotient,
            asymmetry: params.asymmetry,
            aspiration_noise: effective_aspiration(&unit.phoneme, params.aspiration_noise),
        };
        let follows_goat_onset = prev.is_some_and(is_goat_onset);
        let short_final = unit.duration_ms < 100;
        let voiced_tail = pos.index + 1 == pos.total
            && unit.phoneme.is_voiced()
            && !frication
            && !voiced_mixed
            && !(short_final && follows_goat_onset);
        let creak = voiced_tail && !pos.korean;
        let voice: Vec<f32> = match cf0 {
            _ if creak => src.generate_creak(n as f32 / sample_rate as f32, sample_rate),
            Cf0Mode::Decay => {
                src.generate_cf0_glide(n as f32 / sample_rate as f32, sample_rate, unit.f0_end_hz)
            }
            Cf0Mode::Flat => src.generate(n as f32 / sample_rate as f32, sample_rate),
            Cf0Mode::None => {
                src.generate_glide(n as f32 / sample_rate as f32, sample_rate, unit.f0_end_hz)
            }
        };
        if voiced_mixed {
            let noise = frication_noise(n, 0.15);
            voice
                .iter()
                .zip(noise.iter())
                .map(|(g, w)| (g + *w).clamp(-1.0, 1.0))
                .collect()
        } else {
            voice
        }
    };
    let gain = 10f32.powf(segment_gain_db(unit, pos.index, pos.total) / 20.0);
    let mut shaped = filter(&raw);
    for s in shaped.iter_mut() {
        *s *= gain;
    }
    apply_envelope(
        &mut shaped,
        envelope_kind(&unit.phoneme, frication),
        sample_rate,
    );
    let mut cooked = raw;
    for s in cooked.iter_mut() {
        *s *= gain;
    }
    apply_envelope(
        &mut cooked,
        envelope_kind(&unit.phoneme, frication),
        sample_rate,
    );
    (shaped, cooked)
}

struct DiphthongJob<'a> {
    first: &'a ProsodicPhoneme,
    second: &'a ProsodicPhoneme,
    params: &'a SourceParams,
    start: &'a [(f32, f32)],
    end: &'a [(f32, f32)],
    gain_first: f32,
    gain_second: f32,
    sample_rate: u32,
    prev: Option<&'a ProsodicPhoneme>,
}

fn render_diphthong(job: DiphthongJob<'_>) -> (Vec<f32>, Vec<f32>) {
    let first = job.first;
    let second = job.second;
    let params = job.params;
    let start = job.start;
    let end = job.end;
    let sample_rate = job.sample_rate;
    let prev = job.prev;
    let gain_first = job.gain_first;
    let gain_second = job.gain_second;
    let ms = first.duration_ms.saturating_add(second.duration_ms);
    let n = ((ms as f32 / 1000.0) * sample_rate as f32).round().max(1.0) as usize;
    let cf0 = cf0_mode(
        true,
        prev.is_some_and(|p| is_voiceless_obstruent_phoneme(&p.phoneme)),
        first.duration_ms,
    );
    let src = GlottalSource {
        f0_hz: match cf0 {
            Cf0Mode::Flat => first.f0_hz * 1.05,
            _ => first.f0_hz,
        },
        open_quotient: params.open_quotient,
        asymmetry: params.asymmetry,
        aspiration_noise: effective_aspiration(&first.phoneme, params.aspiration_noise),
    };
    let secs = ms as f32 / 1000.0;
    let raw = match cf0 {
        Cf0Mode::Flat => src.generate(secs, sample_rate),
        Cf0Mode::Decay => src.generate_cf0_exp_glide(secs, sample_rate, second.f0_end_hz),
        Cf0Mode::None => src.generate_exp_glide(secs, sample_rate, second.f0_end_hz),
    };
    let mut filter = CascadeFilter::from_pairs(start, sample_rate);
    let mut shaped = Vec::with_capacity(n);
    for (k, x) in raw.iter().enumerate() {
        let t = k as f32 / n.max(1) as f32;
        filter.retune(&lerp_pairs(start, end, t), sample_rate);
        shaped.push(filter.step(*x));
    }
    if let Some((f, b)) = nasal_for_glide(first)
        .or_else(|| nasal_for_glide(second))
        .or_else(|| lateral_for_unit(first, Some(second)))
        .or_else(|| lateral_for_unit(second, None))
    {
        let mut nf = NotchFilter::new(f, b, sample_rate);
        shaped = nf.process(&shaped);
    }
    for (k, s) in shaped.iter_mut().enumerate() {
        let t = k as f32 / n.max(1) as f32;
        *s *= gain_first + (gain_second - gain_first) * t;
    }
    let mut cooked = raw;
    for (k, s) in cooked.iter_mut().enumerate() {
        let t = k as f32 / n.max(1) as f32;
        *s *= gain_first + (gain_second - gain_first) * t;
    }
    (shaped, cooked)
}

fn nasal_for_glide(unit: &ProsodicPhoneme) -> Option<(f32, f32)> {
    let fricative = matches!(
        unit.phoneme.manner(),
        Some(Manner::Fricative | Manner::LateralFricative)
    );
    if unit.is_pause || fricative {
        None
    } else {
        nasal_notch(&unit.phoneme)
    }
}

fn lateral_for_unit(unit: &ProsodicPhoneme, next: Option<&ProsodicPhoneme>) -> Option<(f32, f32)> {
    let fricative = matches!(
        unit.phoneme.manner(),
        Some(Manner::Fricative | Manner::LateralFricative)
    );
    if unit.is_pause || fricative {
        None
    } else if is_lateral_onset(unit) && !unit.word_final {
        if let Some(n) = next {
            if is_vowel(&n.phoneme) && !matches!(n.stress, Stress::Unstressed) {
                return lateral_notch(&unit.phoneme);
            }
        }
        None
    } else {
        None
    }
}

const SMOOTH_MS: f32 = 20.0;

fn smooth_radius(sample_rate: u32) -> usize {
    ((SMOOTH_MS / 1000.0 * sample_rate as f32) as usize).max(1)
}

fn raised_db(a: f32, b: f32, u: f32) -> f32 {
    a + (b - a) * 0.5 * (1.0 - (std::f32::consts::PI * u).cos())
}

fn smooth_work_gains(
    shaped: &mut [Vec<f32>],
    cooked: &mut [Vec<f32>],
    gtracks: &mut [Vec<f32>],
    edges: &[(f32, f32)],
    pauses: &[bool],
    fades: &[usize],
    sample_rate: u32,
) {
    let span = smooth_radius(sample_rate);
    for b in 1..shaped.len() {
        if pauses[b - 1] || pauses[b] {
            continue;
        }
        let (la, lb) = (edges[b - 1].1, edges[b].0);
        if la == lb {
            continue;
        }
        let rb = (span + fades[b] / 2)
            .min(shaped[b - 1].len())
            .min(shaped[b].len())
            .min(cooked[b - 1].len())
            .min(cooked[b].len())
            .min(gtracks[b - 1].len())
            .min(gtracks[b].len());
        if rb == 0 {
            continue;
        }
        let (le0, le1) = edges[b - 1];
        let (re0, re1) = edges[b];
        let ln = shaped[b - 1].len() as f32;
        let rn = shaped[b].len() as f32;
        for k in 0..rb {
            let u = k as f32 / (2.0 * rb as f32);
            let idx = shaped[b - 1].len() - rb + k;
            let base = le0 + (le1 - le0) * (idx as f32 / ln.max(1.0));
            let m = 10f32.powf((raised_db(la, lb, u) - base) / 20.0);
            shaped[b - 1][idx] *= m;
            cooked[b - 1][idx] *= m;
            gtracks[b - 1][idx] *= m;
        }
        for j in 0..rb {
            let u = 0.5 + j as f32 / (2.0 * rb as f32);
            let base = re0 + (re1 - re0) * (j as f32 / rn.max(1.0));
            let m = 10f32.powf((raised_db(la, lb, u) - base) / 20.0);
            shaped[b][j] *= m;
            cooked[b][j] *= m;
            gtracks[b][j] *= m;
        }
    }
}

fn concat_gain_track(tracks: Vec<Vec<f32>>, fades: &[usize]) -> Vec<f32> {
    let mut out: Vec<f32> = Vec::new();
    for (idx, seg) in tracks.iter().enumerate() {
        let want = if idx == 0 { 0 } else { fades[idx] };
        let n = want.min(seg.len()).min(out.len());
        if idx > 0 && n > 0 {
            out.truncate(out.len() - n);
            let tail = &tracks[idx - 1];
            let tail = &tail[tail.len() - n..];
            let head = &seg[..n];
            for k in 0..n {
                let t = k as f32 / n.max(1) as f32;
                out.push((1.0 - t) * tail[k] + t * head[k]);
            }
            out.extend_from_slice(&seg[n..]);
        } else {
            out.extend_from_slice(seg);
        }
    }
    out
}

fn concat_formant_glide(
    shaped: Vec<Vec<f32>>,
    cooked: Vec<Vec<f32>>,
    specs: Vec<FilterSpec>,
    nasals: &[Option<(f32, f32)>],
    fades: &[usize],
    sample_rate: u32,
) -> Vec<f32> {
    let mut out: Vec<f32> = Vec::new();
    for (idx, seg) in shaped.iter().enumerate() {
        let want = if idx == 0 { 0 } else { fades[idx] };
        let n = want.min(seg.len()).min(out.len());
        if idx > 0 && can_glide(&specs[idx - 1], &specs[idx]) && n > 0 {
            out.truncate(out.len() - n);
            let tail = &cooked[idx - 1];
            let head = &cooked[idx];
            let tail = &tail[tail.len().saturating_sub(n)..];
            let head = &head[..head.len().min(n)];
            let nasal = nasals[idx].or(nasals[idx - 1]);
            let glide = filter_glide(tail, head, &specs[idx - 1], &specs[idx], nasal, sample_rate);
            out.extend(glide);
            out.extend_from_slice(&seg[n..]);
        } else {
            for (k, s) in seg.iter().take(n).enumerate() {
                let t = k as f32 / n.max(1) as f32;
                let at = out.len() - n + k;
                out[at] = out[at] * (1.0 - t) + s * t;
            }
            out.extend_from_slice(&seg[n..]);
        }
    }
    out
}

fn is_vowel(p: &articul_phon::Phoneme) -> bool {
    matches!(p.kind, articul_phon::SegmentKind::Vowel { .. })
}

enum WorkUnit {
    Single(usize),
    Merged {
        first: usize,
        second: usize,
        unit: ProsodicPhoneme,
        start: Vec<(f32, f32)>,
        end: Vec<(f32, f32)>,
    },
}

impl WorkUnit {
    fn unit<'a>(&'a self, units: &'a [ProsodicPhoneme]) -> &'a ProsodicPhoneme {
        match self {
            WorkUnit::Single(i) => &units[*i],
            WorkUnit::Merged { unit, .. } => unit,
        }
    }
}

fn render_units(
    units: &[ProsodicPhoneme],
    sample_rate: u32,
    full_pairs: &[(f32, f32)],
    params: &SourceParams,
    korean: bool,
) -> (Vec<f32>, Vec<f32>) {
    let upper = upper_three(full_pairs);
    let short = ((0.008 * sample_rate as f32) as usize).max(1);
    let glide = ((0.050 * sample_rate as f32) as usize).max(1);
    let total = units.len();
    let mut work: Vec<WorkUnit> = Vec::with_capacity(total);
    let mut i = 0usize;
    while i < total {
        if i + 1 < total && is_goat_pair(&units[i], &units[i + 1]) {
            let (start, end) = diphthong_pairs(&units[i], &upper);
            work.push(WorkUnit::Merged {
                first: i,
                second: i + 1,
                unit: ProsodicPhoneme {
                    phoneme: units[i].phoneme.clone(),
                    duration_ms: units[i]
                        .duration_ms
                        .saturating_add(units[i + 1].duration_ms),
                    f0_hz: units[i].f0_hz,
                    f0_end_hz: units[i + 1].f0_end_hz,
                    stress: units[i].stress,
                    is_pause: false,
                    word_final: false,
                },
                start,
                end,
            });
            i += 2;
        } else {
            work.push(WorkUnit::Single(i));
            i += 1;
        }
    }
    let mut specs: Vec<FilterSpec> = Vec::with_capacity(work.len());
    for w in work.iter() {
        match w {
            WorkUnit::Merged { start, .. } => {
                specs.push(FilterSpec::Cascade(start.clone()));
            }
            WorkUnit::Single(oi) => {
                let u = &units[*oi];
                let next = if *oi + 1 < total {
                    Some(&units[*oi + 1])
                } else {
                    None
                };
                let prev = if *oi > 0 { Some(&units[*oi - 1]) } else { None };
                let mut neighbor = next
                    .filter(|p| !is_vowel(&p.phoneme))
                    .or(prev.filter(|p| !is_vowel(&p.phoneme)));
                if is_h_onset(u) || is_lateral_onset(u) {
                    neighbor = next.filter(|p| is_vowel(&p.phoneme)).or(neighbor);
                }
                specs.push(spec_for(u, neighbor, full_pairs, &upper, korean));
            }
        }
    }
    let mut shaped: Vec<Vec<f32>> = Vec::with_capacity(work.len());
    let mut cooked: Vec<Vec<f32>> = Vec::with_capacity(work.len());
    let mut nasals: Vec<Option<(f32, f32)>> = Vec::with_capacity(work.len());
    let edges: Vec<(f32, f32)> = work
        .iter()
        .map(|w| match w {
            WorkUnit::Merged { first, second, .. } => (
                segment_gain_db(&units[*first], *first, total),
                segment_gain_db(&units[*second], *second, total),
            ),
            WorkUnit::Single(oi) => {
                let g = segment_gain_db(&units[*oi], *oi, total);
                (g, g)
            }
        })
        .collect();
    let mut gtracks: Vec<Vec<f32>> = Vec::with_capacity(work.len());
    for w in work.iter() {
        match w {
            WorkUnit::Merged {
                first,
                second,
                start,
                end,
                ..
            } => {
                let g0 = 10f32.powf(edges[gtracks.len()].0 / 20.0);
                let g1 = 10f32.powf(edges[gtracks.len()].1 / 20.0);
                let prev = if *first > 0 {
                    Some(&units[*first - 1])
                } else {
                    None
                };
                let (s, c) = render_diphthong(DiphthongJob {
                    first: &units[*first],
                    second: &units[*second],
                    params,
                    start,
                    end,
                    gain_first: g0,
                    gain_second: g1,
                    sample_rate,
                    prev,
                });
                shaped.push(s);
                cooked.push(c);
                nasals.push(None);
                let n = shaped[shaped.len() - 1].len().max(1) as f32;
                gtracks.push(
                    (0..shaped[shaped.len() - 1].len())
                        .map(|k| g0 + (g1 - g0) * k as f32 / n)
                        .collect(),
                );
            }
            WorkUnit::Single(oi) => {
                let u = &units[*oi];
                let prev = if *oi > 0 { Some(&units[*oi - 1]) } else { None };
                let is_fric = matches!(
                    u.phoneme.manner(),
                    Some(Manner::Fricative | Manner::LateralFricative)
                );
                let nasal = if is_fric {
                    None
                } else {
                    nasal_notch(&u.phoneme)
                };
                let next_for_lateral = if *oi + 1 < total {
                    Some(&units[*oi + 1])
                } else {
                    None
                };
                let lateral = lateral_for_unit(u, next_for_lateral);
                let (mut s, c) = match &specs[shaped.len()] {
                    FilterSpec::Cascade(pairs) => {
                        let filter = CascadeFilter::from_pairs(pairs, sample_rate);
                        let pos = UnitPos {
                            index: *oi,
                            total,
                            korean,
                        };
                        render_unit(u, params, &|x| filter.process(x), sample_rate, &pos, prev)
                    }
                    FilterSpec::Parallel(triples) => {
                        let filter = ParallelFilter::from_pairs(triples, sample_rate);
                        let pos = UnitPos {
                            index: *oi,
                            total,
                            korean,
                        };
                        render_unit(u, params, &|x| filter.process(x), sample_rate, &pos, prev)
                    }
                };
                if let Some((f, b)) = nasal {
                    let mut nf = NotchFilter::new(f, b, sample_rate);
                    s = nf.process(&s);
                }
                if let Some((f, b)) = lateral {
                    let mut lf = NotchFilter::new(f, b, sample_rate);
                    s = lf.process(&s);
                }
                shaped.push(s);
                cooked.push(c);
                nasals.push(nasal.or(lateral));
                let g = 10f32.powf(edges[gtracks.len()].0 / 20.0);
                gtracks.push(vec![g; shaped[shaped.len() - 1].len()]);
            }
        }
    }
    let mut fades = vec![0usize; work.len()];
    for (i, w) in work.windows(2).enumerate() {
        if is_vowel(&w[0].unit(units).phoneme) && is_vowel(&w[1].unit(units).phoneme) {
            fades[i + 1] = glide;
        } else {
            fades[i + 1] = short;
        }
    }
    let pauses: Vec<bool> = work.iter().map(|w| w.unit(units).is_pause).collect();
    smooth_work_gains(
        &mut shaped,
        &mut cooked,
        &mut gtracks,
        &edges,
        &pauses,
        &fades,
        sample_rate,
    );
    let track = concat_gain_track(gtracks, &fades);
    let mixed = concat_formant_glide(shaped, cooked, specs, &nasals, &fades, sample_rate);
    let radiated = apply_radiation(&mixed);
    let mut out = radiated;
    let final_len = work.last().map(|w| {
        let ms = match w {
            WorkUnit::Merged { second, .. } => units[*second].duration_ms,
            WorkUnit::Single(i) => units[*i].duration_ms,
        };
        ((ms as f32 / 1000.0) * sample_rate as f32).round().max(1.0) as usize
    });
    apply_final_fade(&mut out, sample_rate, final_len);
    let leveled = level_output(out, sample_rate);
    (leveled, track)
}

pub fn render_gain_track(text: &str, sample_rate: u32, base_f0: f32) -> Vec<f32> {
    let words = articul_front::normalize(text);
    let parsed = articul_front::parse_utterance(&words);
    if parsed.iter().all(|w| w.phonemes.is_empty()) {
        return Vec::new();
    }
    let planned = articul_front::plan_utterance(&parsed, 1.0, 1.0, base_f0);
    let params = SourceParams {
        open_quotient: 0.6,
        asymmetry: 0.7,
        aspiration_noise: 0.05,
    };
    render_units(&planned, sample_rate, &default_pairs(), &params, false).1
}

pub fn render_sentence(text: &str, sample_rate: u32, base_f0: f32) -> Vec<f32> {
    let words = articul_front::normalize(text);
    let parsed = articul_front::parse_utterance(&words);
    if parsed.iter().all(|w| w.phonemes.is_empty()) {
        return Vec::new();
    }
    let planned = articul_front::plan_utterance(&parsed, 1.0, 1.0, base_f0);
    let params = SourceParams {
        open_quotient: 0.6,
        asymmetry: 0.7,
        aspiration_noise: 0.05,
    };
    render_units(&planned, sample_rate, &default_pairs(), &params, false).0
}

pub fn render_planned(units: &[ProsodicPhoneme], sample_rate: u32) -> Vec<f32> {
    let params = SourceParams {
        open_quotient: 0.6,
        asymmetry: 0.7,
        aspiration_noise: 0.05,
    };
    render_units(units, sample_rate, &default_pairs(), &params, false).0
}

pub fn render_with_voice(text: &str, cfg: &articul_config::VoiceConfig, base_f0: f32) -> Vec<f32> {
    let words = articul_front::normalize(text);
    let parsed = articul_front::parse_utterance(&words);
    if parsed.iter().all(|w| w.phonemes.is_empty()) {
        return Vec::new();
    }
    let korean = cfg.korean.enabled;
    let planned = if korean {
        let boundary = match cfg.korean.final_boundary {
            articul_config::KoreanBoundary::High => articul_front::BoundaryTone::High,
            articul_config::KoreanBoundary::Low => articul_front::BoundaryTone::Low,
        };
        articul_front::plan_utterance_korean(
            &parsed,
            cfg.prosody.rate,
            cfg.prosody.pitch_scale,
            base_f0,
            boundary,
        )
    } else {
        articul_front::plan_utterance(&parsed, cfg.prosody.rate, cfg.prosody.pitch_scale, base_f0)
    };
    let pairs: Vec<(f32, f32)> = cfg.cascade().iter().map(|f| (f.freq_hz, f.bw_hz)).collect();
    let params = SourceParams {
        open_quotient: cfg.source.open_quotient,
        asymmetry: cfg.source.asymmetry,
        aspiration_noise: cfg.source.aspiration_noise,
    };
    render_units(&planned, cfg.sample_rate.hz, &pairs, &params, korean).0
}

fn level_output(mut x: Vec<f32>, sample_rate: u32) -> Vec<f32> {
    if x.is_empty() {
        return x;
    }
    let sr = sample_rate.max(8000) as f32;
    let win = (sr / 50.0).round().max(1.0) as usize;
    let nw = x.len().div_ceil(win);
    let m = (sr * 0.005).round().max(1.0) as usize;
    let mut ring = vec![0.0f32; m];
    let mut rpos = 0usize;
    let mut rcount = 0usize;
    let mut rsum = 0.0f32;
    let p0 = x.iter().map(|v| v.abs()).fold(0.0, f32::max).max(1e-9);
    for v in x.iter_mut() {
        let a = v.abs();
        rsum += a * a - ring[rpos];
        ring[rpos] = a * a;
        rpos += 1;
        if rpos == m {
            rpos = 0;
        }
        rcount += 1;
        let r = (rsum / rcount.min(m) as f32).sqrt();
        let t = (2.2 * r).max(0.05 * p0);
        if a > t {
            *v *= (t + (a - t) * 0.08) / a;
        }
    }
    let mut wrms = vec![0.0f32; nw];
    for (i, w) in wrms.iter_mut().enumerate() {
        let s = i * win;
        let e = (s + win).min(x.len());
        let mut acc = 0.0f32;
        for v in &x[s..e] {
            acc += v * v;
        }
        *w = (acc / (e - s).max(1) as f32).sqrt();
    }
    let peak_env = wrms.iter().fold(0.0f32, |a, b| a.max(*b)).max(1e-9);
    let win_s = win as f32 / sr;
    let attack = (-win_s / 0.012).exp();
    let release = (-win_s / 0.008).exp();
    let mut env_f = vec![0.0f32; nw];
    let mut env = wrms[0].max(peak_env / 1000.0);
    for (i, w) in wrms.iter().enumerate() {
        let target = w.max(peak_env / 1000.0);
        let c = if target > env { attack } else { release };
        env = c * env + (1.0 - c) * target;
        env_f[i] = env;
    }
    let mut gain = vec![1.0f32; nw];
    for (i, g) in gain.iter_mut().enumerate() {
        let e = env_f[i];
        let edb = 20.0 * (e / peak_env).log10();
        let mut gdb = if edb >= -12.0 {
            -0.20 * edb
        } else {
            2.4 - 0.85 * (edb + 12.0)
        };
        if edb > -3.0 {
            gdb -= (edb + 3.0) * 0.5;
        }
        *g = 10.0f32.powf(gdb.min(12.0) / 20.0);
    }
    let gc = (-win_s / 0.010).exp();
    let mut prev = 1.0f32;
    for s in gain.iter_mut() {
        prev = gc * prev + (1.0 - gc) * *s;
        *s = prev;
    }
    for (i, v) in x.iter_mut().enumerate() {
        let pos = i as f32 / win as f32;
        let k = (pos as usize).min(nw - 1);
        let frac = (pos - k as f32).clamp(0.0, 1.0);
        let g0 = gain[k];
        let g1 = if k + 1 < nw { gain[k + 1] } else { gain[k] };
        *v *= g0 + (g1 - g0) * frac;
    }
    let maxv = x.iter().map(|v| v.abs()).fold(0.0, f32::max).max(1e-9);
    let g = 1.10 * 0.989 / maxv;
    for v in x.iter_mut() {
        *v *= g;
    }
    for v in x.iter_mut() {
        *v = v.clamp(-0.989, 0.989);
    }
    x
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn final_fade_confined_to_final_unit() {
        let sr = 22050u32;
        let n = 10000usize;
        let final_unit = 1433usize;
        let mut buf = vec![1.0f32; n];
        apply_final_fade(&mut buf, sr, Some(final_unit));
        for (i, s) in buf.iter().enumerate() {
            if i < n - final_unit {
                assert_eq!(*s, 1.0);
            }
        }
        assert_eq!(buf[n - final_unit], 1.0);
        let floor = 10f32.powf(FINAL_FADE_DB / 20.0);
        assert!((buf[n - 1] - floor).abs() < 1e-5);
    }

    #[test]
    fn final_fade_falls_back_without_unit_length() {
        let sr = 22050u32;
        let n = 10000usize;
        let mut a = vec![1.0f32; n];
        let mut b = vec![1.0f32; n];
        apply_final_fade(&mut a, sr, None);
        apply_final_fade(&mut b, sr, Some(0));
        assert_eq!(a, b);
        let cap = ((FINAL_FADE_MS / 1000.0 * sr as f32) as usize).min(n);
        for (i, s) in a.iter().enumerate() {
            if i < n - cap {
                assert_eq!(*s, 1.0);
            }
        }
        assert!(a[n - 1] < 1.0);
    }

    #[test]
    fn final_fade_caps_at_150ms_for_long_final_unit() {
        let sr = 22050u32;
        let n = 10000usize;
        let cap = ((FINAL_FADE_MS / 1000.0 * sr as f32) as usize).min(n);
        let mut buf = vec![1.0f32; n];
        apply_final_fade(&mut buf, sr, Some(n * 2));
        for (i, s) in buf.iter().enumerate() {
            if i < n - cap {
                assert_eq!(*s, 1.0);
            }
        }
        assert_eq!(buf[n - cap], 1.0);
        assert!(buf[n - cap + 1] < 1.0);
    }
}
