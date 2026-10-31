#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Place {
    Bilabial,
    Labiodental,
    Dental,
    Alveolar,
    Postalveolar,
    Retroflex,
    Palatal,
    Velar,
    Uvular,
    Pharyngeal,
    Glottal,
    Dentolabial,
    Linguolabial,
    Bidental,
    Velopharyngeal,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Manner {
    Plosive,
    Nasal,
    Trill,
    TapFlap,
    Fricative,
    LateralFricative,
    Approximant,
    LateralApproximant,
    Percussive,
    FricatedClick,
    Click,
    Implosive,
    Ejective,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Voicing {
    Voiced,
    Voiceless,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct Secondary {
    pub labialized: bool,
    pub palatalized: bool,
    pub velarized: bool,
    pub pharyngealized: bool,
    pub aspirated: bool,
    pub nasalized: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VowelHeight {
    Close,
    NearClose,
    CloseMid,
    Mid,
    OpenMid,
    NearOpen,
    Open,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VowelBackness {
    Front,
    Central,
    Back,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LengthMark {
    Short,
    HalfLong,
    Long,
    Overlong,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Duration {
    pub phonemic_length: LengthMark,
    pub target_ms: Option<u32>,
}

impl Default for Duration {
    fn default() -> Self {
        Self {
            phonemic_length: LengthMark::Short,
            target_ms: None,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SegmentKind {
    Consonant {
        place: Place,
        manner: Manner,
    },
    Vowel {
        height: VowelHeight,
        backness: VowelBackness,
        rounded: bool,
    },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Phoneme {
    pub base_symbol: String,
    pub kind: SegmentKind,
    pub voicing: Voicing,
    pub secondary: Secondary,
    pub duration: Duration,
}

impl Phoneme {
    pub fn voiceless_consonant(base: char, place: Place, manner: Manner) -> Self {
        Self {
            base_symbol: base.to_string(),
            kind: SegmentKind::Consonant { place, manner },
            voicing: Voicing::Voiceless,
            secondary: Secondary::default(),
            duration: Duration::default(),
        }
    }
    pub fn voiced_consonant(base: char, place: Place, manner: Manner) -> Self {
        Self {
            base_symbol: base.to_string(),
            kind: SegmentKind::Consonant { place, manner },
            voicing: Voicing::Voiced,
            secondary: Secondary::default(),
            duration: Duration::default(),
        }
    }
    pub fn vowel(base: char, height: VowelHeight, backness: VowelBackness, rounded: bool) -> Self {
        Self {
            base_symbol: base.to_string(),
            kind: SegmentKind::Vowel {
                height,
                backness,
                rounded,
            },
            voicing: Voicing::Voiced,
            secondary: Secondary::default(),
            duration: Duration::default(),
        }
    }
    pub fn place(&self) -> Option<Place> {
        match self.kind {
            SegmentKind::Consonant { place, .. } => Some(place),
            SegmentKind::Vowel { .. } => None,
        }
    }
    pub fn manner(&self) -> Option<Manner> {
        match self.kind {
            SegmentKind::Consonant { manner, .. } => Some(manner),
            SegmentKind::Vowel { .. } => None,
        }
    }
    pub fn is_voiced(&self) -> bool {
        self.voicing == Voicing::Voiced
    }
    pub fn is_nasal(&self) -> bool {
        if self.secondary.nasalized {
            return true;
        }
        match self.kind {
            SegmentKind::Consonant { manner, .. } => manner == Manner::Nasal,
            SegmentKind::Vowel { .. } => false,
        }
    }
    pub fn version() -> &'static str {
        "0.0.1"
    }
}

fn is_obstruent_manner(manner: Manner) -> bool {
    matches!(
        manner,
        Manner::Plosive
            | Manner::Fricative
            | Manner::LateralFricative
            | Manner::Ejective
            | Manner::FricatedClick
    )
}

pub fn devoice_obstruent(input: &Phoneme) -> Phoneme {
    let mut out = input.clone();
    if let Some(manner) = input.manner() {
        if input.is_voiced() && is_obstruent_manner(manner) {
            out.voicing = Voicing::Voiceless;
        }
    }
    out
}

pub fn nasalize_vowel(input: &Phoneme) -> Phoneme {
    let mut out = input.clone();
    if matches!(input.kind, SegmentKind::Vowel { .. }) {
        out.secondary.nasalized = true;
    }
    out
}

pub fn apply_rule(input: &Phoneme) -> Phoneme {
    let devoiced = devoice_obstruent(input);
    nasalize_vowel(&devoiced)
}

pub fn version() -> &'static str {
    "0.0.1"
}

fn consonant(symbol: &str, voicing: Voicing, place: Place, manner: Manner) -> Phoneme {
    Phoneme {
        base_symbol: symbol.to_string(),
        kind: SegmentKind::Consonant { place, manner },
        voicing,
        secondary: Secondary::default(),
        duration: Duration::default(),
    }
}

fn vowel_symbol(
    symbol: &str,
    height: VowelHeight,
    backness: VowelBackness,
    rounded: bool,
) -> Phoneme {
    Phoneme {
        base_symbol: symbol.to_string(),
        kind: SegmentKind::Vowel {
            height,
            backness,
            rounded,
        },
        voicing: Voicing::Voiced,
        secondary: Secondary::default(),
        duration: Duration::default(),
    }
}

pub fn lookup(symbol: &str) -> Option<Phoneme> {
    use Manner as M;
    use Place as P;
    use Voicing::{Voiced as Vd, Voiceless as Vl};
    let phoneme = match symbol {
        "p" => consonant(symbol, Vl, P::Bilabial, M::Plosive),
        "b" => consonant(symbol, Vd, P::Bilabial, M::Plosive),
        "m" => consonant(symbol, Vd, P::Bilabial, M::Nasal),
        "ʙ" => consonant(symbol, Vd, P::Bilabial, M::Trill),
        "ɸ" => consonant(symbol, Vl, P::Bilabial, M::Fricative),
        "β" => consonant(symbol, Vd, P::Bilabial, M::Fricative),
        "ɱ" => consonant(symbol, Vd, P::Labiodental, M::Nasal),
        "ⱱ" => consonant(symbol, Vd, P::Labiodental, M::TapFlap),
        "f" => consonant(symbol, Vl, P::Labiodental, M::Fricative),
        "v" => consonant(symbol, Vd, P::Labiodental, M::Fricative),
        "ʋ" => consonant(symbol, Vd, P::Labiodental, M::Approximant),
        "θ" => consonant(symbol, Vl, P::Dental, M::Fricative),
        "ð" => consonant(symbol, Vd, P::Dental, M::Fricative),
        "t" => consonant(symbol, Vl, P::Alveolar, M::Plosive),
        "d" => consonant(symbol, Vd, P::Alveolar, M::Plosive),
        "n" => consonant(symbol, Vd, P::Alveolar, M::Nasal),
        "r" => consonant(symbol, Vd, P::Alveolar, M::Trill),
        "ɾ" => consonant(symbol, Vd, P::Alveolar, M::TapFlap),
        "s" => consonant(symbol, Vl, P::Alveolar, M::Fricative),
        "z" => consonant(symbol, Vd, P::Alveolar, M::Fricative),
        "ɬ" => consonant(symbol, Vl, P::Alveolar, M::LateralFricative),
        "ɮ" => consonant(symbol, Vd, P::Alveolar, M::LateralFricative),
        "ɹ" => consonant(symbol, Vd, P::Alveolar, M::Approximant),
        "l" => consonant(symbol, Vd, P::Alveolar, M::LateralApproximant),
        "ʃ" => consonant(symbol, Vl, P::Postalveolar, M::Fricative),
        "ʒ" => consonant(symbol, Vd, P::Postalveolar, M::Fricative),
        "ʈ" => consonant(symbol, Vl, P::Retroflex, M::Plosive),
        "ɖ" => consonant(symbol, Vd, P::Retroflex, M::Plosive),
        "ɳ" => consonant(symbol, Vd, P::Retroflex, M::Nasal),
        "ʂ" => consonant(symbol, Vl, P::Retroflex, M::Fricative),
        "ʐ" => consonant(symbol, Vd, P::Retroflex, M::Fricative),
        "ɻ" => consonant(symbol, Vd, P::Retroflex, M::Approximant),
        "ɭ" => consonant(symbol, Vd, P::Retroflex, M::LateralApproximant),
        "ɽ" => consonant(symbol, Vd, P::Retroflex, M::TapFlap),
        "c" => consonant(symbol, Vl, P::Palatal, M::Plosive),
        "ɟ" => consonant(symbol, Vd, P::Palatal, M::Plosive),
        "ɲ" => consonant(symbol, Vd, P::Palatal, M::Nasal),
        "ç" => consonant(symbol, Vl, P::Palatal, M::Fricative),
        "ʝ" => consonant(symbol, Vd, P::Palatal, M::Fricative),
        "j" => consonant(symbol, Vd, P::Palatal, M::Approximant),
        "ʎ" => consonant(symbol, Vd, P::Palatal, M::LateralApproximant),
        "k" => consonant(symbol, Vl, P::Velar, M::Plosive),
        "ɡ" => consonant(symbol, Vd, P::Velar, M::Plosive),
        "ŋ" => consonant(symbol, Vd, P::Velar, M::Nasal),
        "x" => consonant(symbol, Vl, P::Velar, M::Fricative),
        "ɣ" => consonant(symbol, Vd, P::Velar, M::Fricative),
        "ɰ" => consonant(symbol, Vd, P::Velar, M::Approximant),
        "ʟ" => consonant(symbol, Vd, P::Velar, M::LateralApproximant),
        "q" => consonant(symbol, Vl, P::Uvular, M::Plosive),
        "ɢ" => consonant(symbol, Vd, P::Uvular, M::Plosive),
        "ɴ" => consonant(symbol, Vd, P::Uvular, M::Nasal),
        "ʀ" => consonant(symbol, Vd, P::Uvular, M::Trill),
        "χ" => consonant(symbol, Vl, P::Uvular, M::Fricative),
        "ʁ" => consonant(symbol, Vd, P::Uvular, M::Fricative),
        "ħ" => consonant(symbol, Vl, P::Pharyngeal, M::Fricative),
        "ʕ" => consonant(symbol, Vd, P::Pharyngeal, M::Fricative),
        "ʡ" => consonant(symbol, Vl, P::Pharyngeal, M::Plosive),
        "ʔ" => consonant(symbol, Vl, P::Glottal, M::Plosive),
        "h" => consonant(symbol, Vl, P::Glottal, M::Fricative),
        "ɦ" => consonant(symbol, Vd, P::Glottal, M::Fricative),
        "i" => vowel_symbol(symbol, VowelHeight::Close, VowelBackness::Front, false),
        "y" => vowel_symbol(symbol, VowelHeight::Close, VowelBackness::Front, true),
        "ɨ" => vowel_symbol(symbol, VowelHeight::Close, VowelBackness::Central, false),
        "ʉ" => vowel_symbol(symbol, VowelHeight::Close, VowelBackness::Central, true),
        "ɯ" => vowel_symbol(symbol, VowelHeight::Close, VowelBackness::Back, false),
        "u" => vowel_symbol(symbol, VowelHeight::Close, VowelBackness::Back, true),
        "ɪ" => vowel_symbol(symbol, VowelHeight::NearClose, VowelBackness::Front, false),
        "ʏ" => vowel_symbol(symbol, VowelHeight::NearClose, VowelBackness::Front, true),
        "ʊ" => vowel_symbol(symbol, VowelHeight::NearClose, VowelBackness::Back, true),
        "e" => vowel_symbol(symbol, VowelHeight::CloseMid, VowelBackness::Front, false),
        "ø" => vowel_symbol(symbol, VowelHeight::CloseMid, VowelBackness::Front, true),
        "ɘ" => vowel_symbol(symbol, VowelHeight::CloseMid, VowelBackness::Central, false),
        "ɵ" => vowel_symbol(symbol, VowelHeight::CloseMid, VowelBackness::Central, true),
        "ɤ" => vowel_symbol(symbol, VowelHeight::CloseMid, VowelBackness::Back, false),
        "o" => vowel_symbol(symbol, VowelHeight::CloseMid, VowelBackness::Back, true),
        "ə" => vowel_symbol(symbol, VowelHeight::Mid, VowelBackness::Central, false),
        "ɛ" => vowel_symbol(symbol, VowelHeight::OpenMid, VowelBackness::Front, false),
        "œ" => vowel_symbol(symbol, VowelHeight::OpenMid, VowelBackness::Front, true),
        "ɜ" => vowel_symbol(symbol, VowelHeight::OpenMid, VowelBackness::Central, false),
        "ɞ" => vowel_symbol(symbol, VowelHeight::OpenMid, VowelBackness::Central, true),
        "ʌ" => vowel_symbol(symbol, VowelHeight::OpenMid, VowelBackness::Back, false),
        "ɔ" => vowel_symbol(symbol, VowelHeight::OpenMid, VowelBackness::Back, true),
        "æ" => vowel_symbol(symbol, VowelHeight::NearOpen, VowelBackness::Front, false),
        "ɐ" => vowel_symbol(symbol, VowelHeight::NearOpen, VowelBackness::Central, false),
        "a" => vowel_symbol(symbol, VowelHeight::Open, VowelBackness::Front, false),
        "ɶ" => vowel_symbol(symbol, VowelHeight::Open, VowelBackness::Front, true),
        "ɑ" => vowel_symbol(symbol, VowelHeight::Open, VowelBackness::Back, false),
        "ɒ" => vowel_symbol(symbol, VowelHeight::Open, VowelBackness::Back, true),
        "ʘ" => consonant(symbol, Vl, P::Bilabial, M::Click),
        "ǀ" => consonant(symbol, Vl, P::Dental, M::Click),
        "ǃ" => consonant(symbol, Vl, P::Postalveolar, M::Click),
        "ǂ" => consonant(symbol, Vl, P::Palatal, M::Click),
        "ǁ" => consonant(symbol, Vl, P::Alveolar, M::Click),
        "ɓ" => consonant(symbol, Vd, P::Bilabial, M::Implosive),
        "ɗ" => consonant(symbol, Vd, P::Alveolar, M::Implosive),
        "ʄ" => consonant(symbol, Vd, P::Palatal, M::Implosive),
        "ɠ" => consonant(symbol, Vd, P::Velar, M::Implosive),
        "ʛ" => consonant(symbol, Vd, P::Uvular, M::Implosive),
        "pʼ" => consonant(symbol, Vl, P::Bilabial, M::Ejective),
        "tʼ" => consonant(symbol, Vl, P::Alveolar, M::Ejective),
        "kʼ" => consonant(symbol, Vl, P::Velar, M::Ejective),
        "sʼ" => consonant(symbol, Vl, P::Alveolar, M::Ejective),
        "ʬ" => consonant(symbol, Vl, P::Bilabial, M::Percussive),
        "ʭ" => consonant(symbol, Vl, P::Bidental, M::Percussive),
        "ʩ" => consonant(symbol, Vl, P::Velopharyngeal, M::Fricative),
        "ʪ" => consonant(symbol, Vd, P::Velopharyngeal, M::Fricative),
        "p͆" => consonant(symbol, Vl, P::Dentolabial, M::Plosive),
        "b͆" => consonant(symbol, Vd, P::Dentolabial, M::Plosive),
        "m͆" => consonant(symbol, Vd, P::Dentolabial, M::Nasal),
        "t̼" => consonant(symbol, Vl, P::Linguolabial, M::Plosive),
        "d̼" => consonant(symbol, Vd, P::Linguolabial, M::Plosive),
        "n̼" => consonant(symbol, Vd, P::Linguolabial, M::Nasal),
        "θ̼" => consonant(symbol, Vl, P::Linguolabial, M::Fricative),
        "ð̼" => consonant(symbol, Vd, P::Linguolabial, M::Fricative),
        _ => return None,
    };
    Some(phoneme)
}
