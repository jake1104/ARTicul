use crate::Stress;
use articul_phon::LengthMark;
use articul_phon::Manner;
use articul_phon::Phoneme;
use articul_phon::Place;
use articul_phon::SegmentKind;
use articul_phon::Voicing;

pub struct ProsodicPhoneme {
    pub phoneme: Phoneme,
    pub duration_ms: u32,
    pub f0_hz: f32,
    pub f0_end_hz: f32,
    pub stress: Stress,
    pub is_pause: bool,
    pub word_final: bool,
}

const DURATION_SALT: u64 = 0x9E3779B97F4A7C15;

fn splitmix64(mut x: u64) -> u64 {
    x = x.wrapping_add(0x9E3779B97F4A7C15);
    let mut z = x;
    z = (z ^ (z >> 30)).wrapping_mul(0xBF58476D1CE4E5B9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94D049BB133111EB);
    z ^ (z >> 31)
}

fn duration_variance(i: usize) -> f32 {
    let r = splitmix64(i as u64 ^ DURATION_SALT) as f32 / u64::MAX as f32;
    1.0 + 0.12 * (r - 0.5)
}

fn length_multiplier(mark: LengthMark) -> f32 {
    match mark {
        LengthMark::Short => 1.0,
        LengthMark::HalfLong => 1.25,
        LengthMark::Long => 1.5,
        LengthMark::Overlong => 2.0,
    }
}

fn intrinsic_ms(p: &Phoneme) -> f32 {
    match &p.kind {
        SegmentKind::Vowel { height, .. } => match height {
            articul_phon::VowelHeight::Close => 155.0,
            articul_phon::VowelHeight::NearClose => 125.0,
            articul_phon::VowelHeight::CloseMid => 160.0,
            articul_phon::VowelHeight::Mid => 110.0,
            articul_phon::VowelHeight::OpenMid => 155.0,
            articul_phon::VowelHeight::NearOpen => 165.0,
            articul_phon::VowelHeight::Open => 180.0,
        },
        SegmentKind::Consonant { manner, .. } => match manner {
            Manner::Fricative | Manner::LateralFricative => {
                if p.voicing == Voicing::Voiced {
                    110.0
                } else {
                    130.0
                }
            }
            Manner::Plosive | Manner::Ejective => 90.0,
            Manner::Nasal | Manner::Approximant | Manner::LateralApproximant => 90.0,
            Manner::Trill => 80.0,
            Manner::TapFlap => 30.0,
            Manner::Click | Manner::Implosive | Manner::Percussive | Manner::FricatedClick => 80.0,
        },
    }
}

fn is_sonorant(p: &Phoneme) -> bool {
    match p.kind {
        SegmentKind::Vowel { .. } => true,
        SegmentKind::Consonant { manner, .. } => matches!(
            manner,
            Manner::Nasal | Manner::Approximant | Manner::LateralApproximant
        ),
    }
}

fn is_voiceless_obstruent(p: &Phoneme) -> bool {
    !p.is_voiced()
        && matches!(
            p.manner(),
            Some(
                Manner::Plosive
                    | Manner::Fricative
                    | Manner::LateralFricative
                    | Manner::Ejective
                    | Manner::FricatedClick
            )
        )
}

fn mindur_ms(p: &Phoneme) -> f32 {
    match p.kind {
        SegmentKind::Vowel { .. } => 40.0,
        SegmentKind::Consonant { manner, .. } => match manner {
            Manner::Fricative | Manner::LateralFricative => 50.0,
            _ => 30.0,
        },
    }
}

fn phrase_st(pos: f32) -> f32 {
    if pos < 0.2 {
        2.0
    } else {
        let e = (-2.0 * (pos - 0.2)).exp();
        let e_end = (-1.6f32).exp();
        -1.0 + 3.0 * (e - e_end) / (1.0 - e_end)
    }
}

fn st_ratio(st: f32) -> f32 {
    2f32.powf(st / 12.0)
}

fn is_full_vowel(p: &Phoneme) -> bool {
    matches!(p.kind, SegmentKind::Vowel { .. })
}

fn is_lateral_approx(p: &Phoneme) -> bool {
    matches!(p.manner(), Some(Manner::LateralApproximant))
}

fn next_is_stressed_vowel(seq: &[Phoneme], stress: &[Stress], i: usize) -> bool {
    if let Some(nxt) = seq.get(i + 1) {
        if is_full_vowel(nxt) {
            return matches!(
                stress.get(i + 1).copied().unwrap_or(Stress::Unstressed),
                Stress::Primary | Stress::Secondary
            );
        }
    }
    false
}

fn find_nucleus(sequence: &[Phoneme], stress: &[Stress]) -> Option<usize> {
    let mut last_primary: Option<usize> = None;
    let mut last_secondary: Option<usize> = None;
    let mut last_vowel: Option<usize> = None;
    for (i, p) in sequence.iter().enumerate() {
        if is_full_vowel(p) {
            last_vowel = Some(i);
            match stress.get(i).copied().unwrap_or(Stress::Unstressed) {
                Stress::Primary => last_primary = Some(i),
                Stress::Secondary => last_secondary = Some(i),
                Stress::Unstressed => {}
            }
        }
    }
    last_primary.or(last_secondary).or(last_vowel)
}

pub fn plan(
    sequence: &[Phoneme],
    stress: &[Stress],
    rate: f32,
    pitch_scale: f32,
    base_f0: f32,
) -> Vec<ProsodicPhoneme> {
    let n = sequence.len();
    if n == 0 {
        return Vec::new();
    }
    let safe_rate = rate.max(0.1);
    let track = f0_track(sequence, stress, base_f0, pitch_scale, &[0]);
    let mut out = Vec::with_capacity(n);
    for (i, p) in sequence.iter().enumerate() {
        let base = intrinsic_ms(p);
        let mult = length_multiplier(p.duration.phonemic_length);
        let stress_f: f32 = match stress.get(i).copied().unwrap_or(Stress::Unstressed) {
            Stress::Unstressed => 0.55,
            Stress::Secondary | Stress::Primary => 1.0,
        };
        let mut ctx_f: f32 = 1.0;
        if is_sonorant(p) {
            if let Some(nxt) = sequence.get(i + 1) {
                if is_voiceless_obstruent(nxt) {
                    ctx_f = 0.78;
                }
            }
        }
        let capped: f32 = (stress_f * ctx_f).max(0.5);
        let mut duration_ms = ((base * mult * capped * duration_variance(i) / safe_rate.powf(0.85))
            .round()
            .max(mindur_ms(p))) as u32;
        let word_final = i + 1 == n;
        if is_lateral_approx(p) && !word_final && next_is_stressed_vowel(sequence, stress, i) {
            duration_ms = duration_ms.max(70);
        }
        let stress_mark = stress.get(i).copied().unwrap_or(Stress::Unstressed);
        let f0_end_hz = if i + 1 < n { track[i + 1] } else { track[i] };
        out.push(ProsodicPhoneme {
            phoneme: p.clone(),
            duration_ms,
            f0_hz: track[i],
            f0_end_hz,
            stress: stress_mark,
            is_pause: false,
            word_final,
        });
    }
    out
}

fn f0_track(
    sequence: &[Phoneme],
    stress: &[Stress],
    base_f0: f32,
    pitch_scale: f32,
    phrase_starts: &[usize],
) -> Vec<f32> {
    let n = sequence.len();
    let nucleus = find_nucleus(sequence, stress);
    let phrase_of = |i: usize| -> (usize, usize) {
        let mut start = 0usize;
        for s in phrase_starts {
            if *s <= i {
                start = *s;
            }
        }
        let mut end = n;
        for s in phrase_starts {
            if *s > i && *s < end {
                end = *s;
            }
        }
        (start, end)
    };
    let phrase_pos = |i: usize| {
        let (ps, pe) = phrase_of(i);
        let span = pe.saturating_sub(ps + 1).max(1) as f32;
        (i.saturating_sub(ps)) as f32 / span
    };
    struct Accent {
        idx: usize,
        amp: f32,
    }
    let mut accents: Vec<Accent> = Vec::new();
    if let Some(nuc) = nucleus {
        let mut prior = 0usize;
        for (i, p) in sequence.iter().enumerate() {
            if i > nuc {
                break;
            }
            if is_full_vowel(p) {
                if i == nuc {
                    accents.push(Accent { idx: i, amp: 5.0 });
                } else {
                    match stress.get(i).copied().unwrap_or(Stress::Unstressed) {
                        Stress::Primary => {
                            accents.push(Accent {
                                idx: i,
                                amp: 3.0 - 1.5 * prior as f32,
                            });
                            prior += 1;
                        }
                        Stress::Secondary => {
                            accents.push(Accent {
                                idx: i,
                                amp: 1.5 - 1.5 * prior as f32,
                            });
                            prior += 1;
                        }
                        Stress::Unstressed => {}
                    }
                }
            }
        }
    }
    let mut track = Vec::with_capacity(n);
    for i in 0..n {
        let pos = phrase_pos(i);
        let st = match nucleus {
            None => {
                if n > 1 && i + 1 == n {
                    -7.0
                } else {
                    phrase_st(pos)
                }
            }
            Some(nuc) => {
                if i == nuc {
                    phrase_st(pos) + 5.0
                } else if n > 1 && i + 1 == n {
                    -7.0
                } else {
                    let mut tail = 0.0f32;
                    for a in &accents {
                        if a.idx == i + 1 {
                            tail += 0.3 * a.amp;
                        } else if a.idx <= i {
                            tail += a.amp * 0.5f32.powf((i - a.idx) as f32);
                        }
                    }
                    phrase_st(pos) + tail
                }
            }
        };
        track.push(base_f0 * pitch_scale * st_ratio(st));
    }
    track
}

pub struct WordProsody {
    pub phonemes: Vec<Phoneme>,
    pub stress: Vec<Stress>,
    pub boundary_after: f32,
    pub function_word: bool,
    pub emphasized: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BoundaryTone {
    High,
    Low,
}

fn is_tense_fricative_onset(p: &Phoneme) -> bool {
    if !matches!(p.manner(), Some(Manner::Fricative)) {
        return false;
    }
    matches!(p.place(), Some(Place::Glottal))
        || (!p.is_voiced() && matches!(p.place(), Some(Place::Alveolar)))
}

fn korean_anchors(n: usize, tense: bool, boundary_st: f32, final_word: bool) -> Vec<f32> {
    let t = if tense { 1.0 } else { -1.0 };
    let mut out = match n {
        0 => Vec::new(),
        1 => vec![0.0],
        2 => vec![t, 1.5],
        3 => vec![t, 1.5, 1.5],
        _ => {
            let mut v = vec![t, 1.5];
            for j in 2..n - 2 {
                let f = (j - 1) as f32 / (n - 3) as f32;
                v.push(1.5 + (-0.5 - 1.5) * f);
            }
            v.push(-0.5);
            v.push(1.5);
            v
        }
    };
    if final_word {
        if let Some(last) = out.last_mut() {
            *last = boundary_st;
        }
    }
    out
}

fn korean_word_st(t: f32, vowels: &[usize], anchors: &[f32], tense: bool) -> f32 {
    if vowels.is_empty() || anchors.is_empty() {
        return if tense { 1.0 } else { -1.0 };
    }
    let m = vowels.len();
    if t < vowels[0] as f32 {
        return anchors[0];
    }
    for j in 0..m {
        let v = vowels[j] as f32;
        if t >= v && t < v + 1.0 {
            return anchors[j];
        }
        if j + 1 < m {
            let nxt = vowels[j + 1] as f32;
            if t >= v + 1.0 && t < nxt {
                let span = (nxt - v - 1.0).max(1e-6);
                let f = (t - v - 1.0) / span;
                return anchors[j] + (anchors[j + 1] - anchors[j]) * f;
            }
        }
    }
    anchors[m - 1]
}

pub fn plan_utterance_korean(
    words: &[WordProsody],
    rate: f32,
    pitch_scale: f32,
    base_f0: f32,
    boundary: BoundaryTone,
) -> Vec<ProsodicPhoneme> {
    let mut flat_seq: Vec<Phoneme> = Vec::new();
    for w in words.iter() {
        for p in w.phonemes.iter() {
            flat_seq.push(p.clone());
        }
    }
    let n = flat_seq.len();
    if n == 0 {
        return Vec::new();
    }
    let safe_rate = rate.max(0.1);
    let boundary_st = match boundary {
        BoundaryTone::High => 3.0,
        BoundaryTone::Low => -3.5,
    };
    let mut word_vowels: Vec<Vec<usize>> = Vec::with_capacity(words.len());
    let mut cursor = 0usize;
    for w in words.iter() {
        let mut v = Vec::new();
        for (k, p) in w.phonemes.iter().enumerate() {
            if is_full_vowel(p) {
                v.push(cursor + k);
            }
        }
        cursor += w.phonemes.len();
        word_vowels.push(v);
    }
    let last_word = words.len() - 1;
    let mut st_track = vec![0.0f32; n];
    let mut st_end_track = vec![0.0f32; n];
    let mut seg = 0usize;
    for (wi, w) in words.iter().enumerate() {
        let vowels = &word_vowels[wi];
        let tense = w.phonemes.first().is_some_and(is_tense_fricative_onset);
        let anchors = korean_anchors(vowels.len(), tense, boundary_st, wi == last_word);
        for k in 0..w.phonemes.len() {
            st_track[seg + k] = korean_word_st(seg as f32 + k as f32, vowels, &anchors, tense);
            st_end_track[seg + k] =
                korean_word_st(seg as f32 + k as f32 + 1.0, vowels, &anchors, tense);
        }
        seg += w.phonemes.len();
    }
    let final_vowel_flat = word_vowels[last_word].last().copied().unwrap_or(n);
    let flat_unstressed = vec![Stress::Unstressed; n];
    let mut out = Vec::with_capacity(n + words.len());
    let mut fi = 0usize;
    for (wi, w) in words.iter().enumerate() {
        let local_last = word_vowels[wi].last().map(|v| v - fi);
        for (k, p) in w.phonemes.iter().enumerate() {
            let base = intrinsic_ms(p);
            let mult = length_multiplier(p.duration.phonemic_length);
            let mut ctx_f: f32 = 1.0;
            if is_sonorant(p) {
                if let Some(nxt) = flat_seq.get(fi + 1) {
                    if is_voiceless_obstruent(nxt) {
                        ctx_f = 0.78;
                    }
                }
            }
            let poly_f = match word_vowels[wi].len() {
                0 | 1 => 1.0,
                2 => 0.9,
                _ => 0.8,
            };
            let func_f = if w.function_word && !w.emphasized {
                0.8
            } else {
                1.0
            };
            let cluster_f = if !is_full_vowel(p) && fi > 0 && !is_full_vowel(&flat_seq[fi - 1]) {
                0.8
            } else {
                1.0
            };
            let initial_f = if k == 0 && !is_full_vowel(p) {
                1.1
            } else {
                1.0
            };
            let final_f = if wi == last_word && local_last.is_some_and(|lv| k >= lv) {
                1.6
            } else {
                1.0
            };
            let capped: f32 = ctx_f.max(0.5);
            let mut duration_ms = ((base
                * mult
                * capped
                * poly_f
                * func_f
                * cluster_f
                * final_f
                * initial_f
                * duration_variance(fi)
                / safe_rate.powf(0.85))
            .round()
            .max(mindur_ms(p))) as u32;
            let word_final = k + 1 == w.phonemes.len();
            if is_lateral_approx(p)
                && !word_final
                && next_is_stressed_vowel(&flat_seq, &flat_unstressed, fi)
            {
                duration_ms = duration_ms.max(70);
            }
            let mut f0_hz = base_f0 * pitch_scale * st_ratio(st_track[fi]);
            let mut f0_end_hz = base_f0 * pitch_scale * st_ratio(st_end_track[fi]);
            if matches!(boundary, BoundaryTone::Low) && fi >= final_vowel_flat {
                f0_hz = f0_hz.max(100.0);
                f0_end_hz = f0_end_hz.max(100.0);
            }
            out.push(ProsodicPhoneme {
                phoneme: p.clone(),
                duration_ms,
                f0_hz,
                f0_end_hz,
                stress: Stress::Unstressed,
                is_pause: false,
                word_final,
            });
            fi += 1;
        }
        if wi + 1 < words.len() && !w.phonemes.is_empty() && w.boundary_after >= 0.4 {
            let pause_ms = (400.0 * w.boundary_after).round().max(1.0) as u32;
            out.push(ProsodicPhoneme {
                phoneme: w
                    .phonemes
                    .last()
                    .cloned()
                    .unwrap_or_else(|| flat_seq[0].clone()),
                duration_ms: pause_ms,
                f0_hz: 0.0,
                f0_end_hz: 0.0,
                stress: Stress::Unstressed,
                is_pause: true,
                word_final: true,
            });
        }
    }
    out
}

const FUNCTION_WORDS: &[&str] = &[
    "D@", "Di", "@", "{", "DIs", "Diz", "D{t", "d@t", "aI", "ju", "hi", "Si", "It", "wi", "DeI",
    "mi", "hIm", "h3", "Vs", "DEm", "maI", "jO", "jOr", "hIz", "h3z", "Its", "aU@", "wVt", "sVm",
    "Eni", "noU", "hu", "wIC", "tu", "t@", "tI", "fO", "frVm", "Qv", "In", "Qn", "{t", "wIT",
    "baI", "aUt", "Qf", "Intu", "Vp", "daUn", "ni@", "bI", "Iz", "Ar", "wVz", "w3", "bin", "h{v",
    "h{z", "h{d", "du", "dVz", "dId", "dVn", "wIl", "wUd", "S{l", "SUd", "k{n", "kUd", "meI",
    "maIt", "mVst", "{nd", "{n", "nd", "bVt", "O", "nO", "If", "D{n", "s@U", "bIkQz", "bIkQs",
    "jEt", "stIl", "v3ri", "kwI", "dZVst", "oUnli",
];

fn boundary_strength(word: &str) -> f32 {
    let mut strength = 0.0f32;
    for c in word.chars() {
        let s = match c {
            '.' | '!' => 1.0,
            '|' => 0.6,
            ';' | ':' => 0.5,
            ',' => 0.4,
            _ => 0.0,
        };
        if s > strength {
            strength = s;
        }
    }
    strength
}

fn lexicon_key(word: &str) -> String {
    word.chars()
        .filter(|c| !matches!(c, '"' | '%' | ',' | ';' | ':' | '|' | '.' | '!'))
        .collect()
}

pub fn parse_utterance(words: &[String]) -> Vec<WordProsody> {
    let transcriber = crate::Xsampa::new();
    let mut parsed = Vec::with_capacity(words.len());
    for (wi, w) in words.iter().enumerate() {
        let (phonemes, stress) = transcriber.transcribe(w);
        let mut boundary = boundary_strength(w);
        if wi + 1 == words.len() {
            boundary = boundary.max(1.0);
        }
        let emphasized = stress
            .iter()
            .any(|s| matches!(s, Stress::Primary | Stress::Secondary));
        let function_word = FUNCTION_WORDS.contains(&lexicon_key(w).as_str());
        parsed.push(WordProsody {
            phonemes,
            stress,
            boundary_after: boundary,
            function_word,
            emphasized,
        });
    }
    parsed
}

pub fn plan_utterance(
    words: &[WordProsody],
    rate: f32,
    pitch_scale: f32,
    base_f0: f32,
) -> Vec<ProsodicPhoneme> {
    let mut flat_seq: Vec<Phoneme> = Vec::new();
    let mut flat_stress: Vec<Stress> = Vec::new();
    for w in words.iter() {
        for (k, p) in w.phonemes.iter().enumerate() {
            flat_seq.push(p.clone());
            flat_stress.push(w.stress.get(k).copied().unwrap_or(Stress::Unstressed));
        }
    }
    let n = flat_seq.len();
    if n == 0 {
        return Vec::new();
    }
    let safe_rate = rate.max(0.1);
    let mut phrase_starts = vec![0usize];
    let mut seg = 0usize;
    for (wi, w) in words.iter().enumerate() {
        if wi > 0 && words[wi - 1].boundary_after >= 0.5 {
            phrase_starts.push(seg);
        }
        seg += w.phonemes.len();
    }
    let track = f0_track(
        &flat_seq,
        &flat_stress,
        base_f0,
        pitch_scale,
        &phrase_starts,
    );
    let mut word_syllables = vec![0usize; words.len()];
    let mut word_last_vowel = vec![None::<usize>; words.len()];
    for (wi, w) in words.iter().enumerate() {
        let mut count = 0usize;
        let mut last = None;
        for (k, p) in w.phonemes.iter().enumerate() {
            if is_full_vowel(p) {
                count += 1;
                last = Some(k);
            }
        }
        word_syllables[wi] = count;
        word_last_vowel[wi] = last;
    }
    let mut out = Vec::with_capacity(n + words.len());
    let mut fi = 0usize;
    for (wi, w) in words.iter().enumerate() {
        for (k, p) in w.phonemes.iter().enumerate() {
            let base = intrinsic_ms(p);
            let mult = length_multiplier(p.duration.phonemic_length);
            let stress_f: f32 = match flat_stress.get(fi).copied().unwrap_or(Stress::Unstressed) {
                Stress::Unstressed => 0.55,
                Stress::Secondary | Stress::Primary => 1.0,
            };
            let mut ctx_f: f32 = 1.0;
            if is_sonorant(p) {
                if let Some(nxt) = flat_seq.get(fi + 1) {
                    if is_voiceless_obstruent(nxt) {
                        ctx_f = 0.78;
                    }
                }
            }
            let poly_f = match word_syllables[wi] {
                0 | 1 => 1.0,
                2 => 0.9,
                _ => 0.8,
            };
            let func_f = if w.function_word && !w.emphasized {
                0.8
            } else {
                1.0
            };
            let cluster_f = if !is_full_vowel(p) && fi > 0 && !is_full_vowel(&flat_seq[fi - 1]) {
                0.8
            } else {
                1.0
            };
            let initial_f = if k == 0 && !is_full_vowel(p) {
                1.1
            } else {
                1.0
            };
            let tier = if w.boundary_after >= 1.0 {
                1.3
            } else if w.boundary_after >= 0.4 {
                1.15
            } else {
                1.0
            };
            let final_f = if w.boundary_after > 0.0 {
                match word_last_vowel[wi] {
                    Some(lv) if k >= lv => tier,
                    _ => 1.0,
                }
            } else {
                1.0
            };
            let capped: f32 = (stress_f * ctx_f).max(0.5);
            let mut duration_ms = ((base
                * mult
                * capped
                * poly_f
                * func_f
                * cluster_f
                * final_f
                * initial_f
                * duration_variance(fi)
                / safe_rate.powf(0.85))
            .round()
            .max(mindur_ms(p))) as u32;
            let word_final = k + 1 == w.phonemes.len();
            if is_lateral_approx(p)
                && !word_final
                && next_is_stressed_vowel(&flat_seq, &flat_stress, fi)
            {
                duration_ms = duration_ms.max(70);
            }
            let stress_mark = flat_stress.get(fi).copied().unwrap_or(Stress::Unstressed);
            let f0_end_hz = if fi + 1 < n { track[fi + 1] } else { track[fi] };
            out.push(ProsodicPhoneme {
                phoneme: p.clone(),
                duration_ms,
                f0_hz: track[fi],
                f0_end_hz,
                stress: stress_mark,
                is_pause: false,
                word_final,
            });
            fi += 1;
        }
        if wi + 1 < words.len() && !w.phonemes.is_empty() && w.boundary_after >= 0.4 {
            let pause_ms = (400.0 * w.boundary_after).round().max(1.0) as u32;
            out.push(ProsodicPhoneme {
                phoneme: w
                    .phonemes
                    .last()
                    .cloned()
                    .unwrap_or_else(|| flat_seq[0].clone()),
                duration_ms: pause_ms,
                f0_hz: 0.0,
                f0_end_hz: 0.0,
                stress: Stress::Unstressed,
                is_pause: true,
                word_final: true,
            });
        }
    }
    out
}
