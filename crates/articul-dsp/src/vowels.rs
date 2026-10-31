use articul_phon::Phoneme;
use articul_phon::SegmentKind;
use articul_phon::VowelBackness;
use articul_phon::VowelHeight;

pub fn vowel_formants(phoneme: &Phoneme) -> Option<(f32, f32, f32)> {
    let SegmentKind::Vowel {
        height,
        backness,
        rounded,
    } = phoneme.kind
    else {
        return None;
    };
    let f1 = match height {
        VowelHeight::Close => 280.0,
        VowelHeight::NearClose => 400.0,
        VowelHeight::CloseMid => 480.0,
        VowelHeight::Mid => 520.0,
        VowelHeight::OpenMid => 600.0,
        VowelHeight::NearOpen => 690.0,
        VowelHeight::Open => 730.0,
    };
    let f2 = match (height, backness, rounded) {
        (VowelHeight::Mid, _, _) => 1500.0,
        (VowelHeight::Close, VowelBackness::Front, false) => 2300.0,
        (VowelHeight::Close, VowelBackness::Front, true) => 1950.0,
        (VowelHeight::Close, VowelBackness::Central, false) => 1500.0,
        (VowelHeight::Close, VowelBackness::Central, true) => 1300.0,
        (VowelHeight::Close, VowelBackness::Back, false) => 1150.0,
        (VowelHeight::Close, VowelBackness::Back, true) => 870.0,
        (VowelHeight::NearClose, VowelBackness::Front, false) => 2100.0,
        (VowelHeight::NearClose, VowelBackness::Front, true) => 1750.0,
        (VowelHeight::NearClose, VowelBackness::Central, false) => 1400.0,
        (VowelHeight::NearClose, VowelBackness::Central, true) => 1200.0,
        (VowelHeight::NearClose, VowelBackness::Back, false) => 1250.0,
        (VowelHeight::NearClose, VowelBackness::Back, true) => 1000.0,
        (VowelHeight::CloseMid, VowelBackness::Front, false) => 1950.0,
        (VowelHeight::CloseMid, VowelBackness::Front, true) => 1650.0,
        (VowelHeight::CloseMid, VowelBackness::Central, false) => 1450.0,
        (VowelHeight::CloseMid, VowelBackness::Central, true) => 1250.0,
        (VowelHeight::CloseMid, VowelBackness::Back, false) => 1100.0,
        (VowelHeight::CloseMid, VowelBackness::Back, true) => 950.0,
        (VowelHeight::OpenMid, VowelBackness::Front, false) => 1720.0,
        (VowelHeight::OpenMid, VowelBackness::Front, true) => 1480.0,
        (VowelHeight::OpenMid, VowelBackness::Central, false) => 1400.0,
        (VowelHeight::OpenMid, VowelBackness::Central, true) => 1200.0,
        (VowelHeight::OpenMid, VowelBackness::Back, false) => 1150.0,
        (VowelHeight::OpenMid, VowelBackness::Back, true) => 840.0,
        (VowelHeight::NearOpen, VowelBackness::Front, false) => 1700.0,
        (VowelHeight::NearOpen, VowelBackness::Front, true) => 1450.0,
        (VowelHeight::NearOpen, VowelBackness::Central, false) => 1400.0,
        (VowelHeight::NearOpen, VowelBackness::Central, true) => 1200.0,
        (VowelHeight::NearOpen, VowelBackness::Back, false) => 1250.0,
        (VowelHeight::NearOpen, VowelBackness::Back, true) => 950.0,
        (VowelHeight::Open, VowelBackness::Front, false) => 1250.0,
        (VowelHeight::Open, VowelBackness::Front, true) => 1100.0,
        (VowelHeight::Open, VowelBackness::Central, false) => 1400.0,
        (VowelHeight::Open, VowelBackness::Central, true) => 1200.0,
        (VowelHeight::Open, VowelBackness::Back, false) => 1050.0,
        (VowelHeight::Open, VowelBackness::Back, true) => 900.0,
    };
    let hi = match height {
        VowelHeight::Close => 0.0,
        VowelHeight::NearClose => 1.5,
        VowelHeight::CloseMid => 2.5,
        VowelHeight::Mid => 3.0,
        VowelHeight::OpenMid => 4.0,
        VowelHeight::NearOpen => 5.0,
        VowelHeight::Open => 5.5,
    };
    let mut f3 = 2500.0 - 20.0 * hi;
    match backness {
        VowelBackness::Front => f3 += 250.0,
        VowelBackness::Central => {}
        VowelBackness::Back => f3 -= 150.0,
    }
    Some((f1, f2, f3))
}

pub fn locus_adjusted_formants(vowel: &Phoneme, neighbor: &Phoneme) -> Option<(f32, f32, f32)> {
    let (f1, f2, f3) = vowel_formants(vowel)?;
    if !is_consonant(neighbor) {
        return Some((f1, f2, f3));
    }
    let place = neighbor.place()?;
    Some(locus_pull_toward(f1, f2, f3, place))
}

pub fn locus_pull_toward(f1: f32, f2: f32, f3: f32, place: articul_phon::Place) -> (f32, f32, f32) {
    let (k, c) = match place {
        articul_phon::Place::Bilabial | articul_phon::Place::Labiodental => (0.7, 300.0),
        articul_phon::Place::Dental
        | articul_phon::Place::Alveolar
        | articul_phon::Place::Postalveolar
        | articul_phon::Place::Retroflex => (0.3, 1100.0),
        articul_phon::Place::Velar => (0.5, 1200.0),
        _ => return (f1, f2, f3),
    };
    let f3 = match place {
        articul_phon::Place::Velar => f3 + 0.3 * (2600.0 - f3),
        _ => f3,
    };
    (f1, k * f2 + c, f3)
}

pub fn reduced_vowel_targets(phoneme: &Phoneme, stressed: bool) -> Option<(f32, f32, f32)> {
    let (f1, f2, f3) = vowel_formants(phoneme)?;
    if stressed {
        return Some((f1, f2, f3));
    }
    Some((f1 + 0.3 * (520.0 - f1), f2 + 0.3 * (1400.0 - f2), f3))
}

fn is_consonant(p: &Phoneme) -> bool {
    matches!(p.kind, SegmentKind::Consonant { .. })
}

pub fn korean_vowel_formants(phoneme: &Phoneme) -> Option<(f32, f32, f32)> {
    match phoneme.base_symbol.as_str() {
        "a" => Some((690.0, 1165.0, 2930.0)),
        "ʌ" => Some((585.0, 1085.0, 2707.0)),
        "e" => Some((479.0, 1919.0, 2857.0)),
        "o" => Some((441.0, 740.0, 2481.0)),
        "u" => Some((253.0, 689.0, 2415.0)),
        "ɯ" => Some((369.0, 1503.0, 2674.0)),
        _ => None,
    }
}

fn is_back_vowel(p: &Phoneme) -> bool {
    matches!(
        p.kind,
        SegmentKind::Vowel {
            backness: VowelBackness::Back,
            ..
        }
    )
}

pub fn korean_locus_pull(
    f1: f32,
    f2: f32,
    f3: f32,
    vowel: &Phoneme,
    neighbor: &Phoneme,
) -> (f32, f32, f32) {
    let Some(place) = neighbor.place() else {
        return (f1, f2, f3);
    };
    if matches!(place, articul_phon::Place::Velar) && is_back_vowel(vowel) {
        return (f1, f2, f3);
    }
    let (pf1, pf2, pf3) = locus_pull_toward(f1, f2, f3, place);
    if vowel.base_symbol == "a" && neighbor.is_nasal() {
        (pf1, f2 + 0.5 * (pf2 - f2), f3 + 0.5 * (pf3 - f3))
    } else {
        (pf1, pf2, pf3)
    }
}
