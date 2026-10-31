use crate::Stress;
use articul_phon::LengthMark;
use articul_phon::Manner;
use articul_phon::Phoneme;
use articul_phon::Place;
use articul_phon::SegmentKind;
use articul_phon::Voicing;

pub struct Xsampa {
    table: Vec<(&'static str, &'static str)>,
}

impl Xsampa {
    pub fn new() -> Self {
        Self {
            table: default_table(),
        }
    }

    pub fn with_table(table: Vec<(&'static str, &'static str)>) -> Self {
        Self { table }
    }

    pub fn transcribe(&self, word: &str) -> (Vec<Phoneme>, Vec<Stress>) {
        let chars: Vec<char> = word.chars().collect();
        let mut out = Vec::new();
        let mut marks = Vec::new();
        let mut pending = Stress::Unstressed;
        let mut i = 0;
        while i < chars.len() {
            if chars[i] == '"' {
                pending = Stress::Primary;
                i += 1;
                continue;
            }
            if chars[i] == '%' {
                pending = Stress::Secondary;
                i += 1;
                continue;
            }
            if chars[i] == '<' {
                if let Some(end) = chars[i..].iter().position(|&c| c == '>') {
                    if end <= 6 {
                        i += end + 1;
                        continue;
                    }
                }
                i += 1;
                continue;
            }
            let mut hit: Option<(&str, &str)> = None;
            let mut taken = 0;
            for len in (1..=4).rev() {
                if i + len > chars.len() {
                    continue;
                }
                let s: String = chars[i..i + len].iter().collect();
                if let Some(e) = self.table.iter().find(|(k, _)| *k == s) {
                    hit = Some(*e);
                    taken = len;
                    break;
                }
            }
            let Some((token, ipa)) = hit else {
                i += 1;
                continue;
            };
            let Some(mut phon) = articul_phon::lookup(ipa) else {
                i += taken;
                continue;
            };
            if token == "5" {
                phon.secondary.velarized = true;
            }
            i += taken;
            i = apply_suffixes(&mut phon, &chars, i);
            let mark = match phon.kind {
                SegmentKind::Vowel { .. } => {
                    let m = pending;
                    pending = Stress::Unstressed;
                    m
                }
                _ => Stress::Unstressed,
            };
            marks.push(mark);
            out.push(phon);
        }
        (out, marks)
    }
}

fn apply_suffixes(phon: &mut Phoneme, chars: &[char], mut i: usize) -> usize {
    loop {
        if starts_with(chars, i, ":\\") {
            phon.duration.phonemic_length = LengthMark::Long;
            i += 2;
        } else if starts_with(chars, i, "_?\\") {
            phon.secondary.pharyngealized = true;
            i += 3;
        } else if starts_with(chars, i, "_<") {
            if let Some(q) = try_implosive(phon) {
                *phon = q;
            }
            i += 2;
        } else if starts_with(chars, i, "_>") {
            if let Some(q) = try_ejective(phon) {
                *phon = q;
            }
            i += 2;
        } else if starts_with(chars, i, "_~") {
            phon.secondary.nasalized = true;
            i += 2;
        } else if starts_with(chars, i, "_h") {
            phon.secondary.aspirated = true;
            i += 2;
        } else if starts_with(chars, i, "_w") {
            phon.secondary.labialized = true;
            i += 2;
        } else if starts_with(chars, i, "_j") {
            phon.secondary.palatalized = true;
            i += 2;
        } else if starts_with(chars, i, "_G") || starts_with(chars, i, "_e") {
            phon.secondary.velarized = true;
            i += 2;
        } else if starts_with(chars, i, "_d") {
            set_place(phon, Place::Dental);
            i += 2;
        } else if starts_with(chars, i, "_N") {
            set_place(phon, Place::Linguolabial);
            i += 2;
        } else if starts_with(chars, i, "_0") {
            phon.voicing = Voicing::Voiceless;
            i += 2;
        } else if starts_with(chars, i, "_v") {
            phon.voicing = Voicing::Voiced;
            i += 2;
        } else if starts_with(chars, i, ":") {
            phon.duration.phonemic_length = LengthMark::Long;
            i += 1;
        } else if i < chars.len() && chars[i] == '~' {
            phon.secondary.nasalized = true;
            i += 1;
        } else if i < chars.len() && chars[i] == '\'' {
            phon.secondary.palatalized = true;
            i += 1;
        } else if i < chars.len() && matches!(chars[i], '.' | '|' | '-' | '=' | '`' | '^' | '!') {
            i += 1;
        } else if ["_=", "_^", "_}"].iter().any(|p| starts_with(chars, i, p)) {
            i += 2;
        } else if i < chars.len() && chars[i] == '_' {
            i += 1;
            while i < chars.len() && chars[i].is_ascii_alphanumeric() {
                i += 1;
            }
        } else {
            break;
        }
    }
    i
}

fn starts_with(chars: &[char], i: usize, pat: &str) -> bool {
    let p: Vec<char> = pat.chars().collect();
    i + p.len() <= chars.len() && chars[i..i + p.len()] == p[..]
}

fn set_place(phon: &mut Phoneme, place: Place) {
    if let SegmentKind::Consonant { manner, .. } = phon.kind {
        phon.kind = SegmentKind::Consonant { place, manner };
    }
}

fn try_implosive(phon: &Phoneme) -> Option<Phoneme> {
    let SegmentKind::Consonant { place, manner } = phon.kind else {
        return None;
    };
    if manner != Manner::Plosive || !phon.is_voiced() {
        return None;
    }
    let symbol = match place {
        Place::Bilabial => "ɓ",
        Place::Alveolar => "ɗ",
        Place::Palatal => "ʄ",
        Place::Velar => "ɠ",
        Place::Uvular => "ʛ",
        _ => return None,
    };
    articul_phon::lookup(symbol)
}

fn try_ejective(phon: &Phoneme) -> Option<Phoneme> {
    let SegmentKind::Consonant { manner, .. } = phon.kind else {
        return None;
    };
    if phon.is_voiced() {
        return None;
    }
    if !matches!(
        manner,
        Manner::Plosive | Manner::Fricative | Manner::LateralFricative
    ) {
        return None;
    }
    articul_phon::lookup(&format!("{}ʼ", phon.base_symbol))
}

impl Default for Xsampa {
    fn default() -> Self {
        Self::new()
    }
}

fn default_table() -> Vec<(&'static str, &'static str)> {
    vec![
        ("p", "p"),
        ("b", "b"),
        ("m", "m"),
        ("B\\", "ʙ"),
        ("p\\", "ɸ"),
        ("B", "β"),
        ("F", "ɱ"),
        ("4", "ɾ"),
        ("f", "f"),
        ("v", "v"),
        ("v\\", "ʋ"),
        ("P", "ʋ"),
        ("T", "θ"),
        ("D", "ð"),
        ("t", "t"),
        ("d", "d"),
        ("n", "n"),
        ("r", "r"),
        ("r\\", "ɹ"),
        ("r`", "ɽ"),
        ("r\\`", "ɻ"),
        ("s", "s"),
        ("z", "z"),
        ("K", "ɬ"),
        ("K\\", "ɮ"),
        ("l", "l"),
        ("l`", "ɭ"),
        ("S", "ʃ"),
        ("Z", "ʒ"),
        ("t`", "ʈ"),
        ("d`", "ɖ"),
        ("n`", "ɳ"),
        ("s`", "ʂ"),
        ("z`", "ʐ"),
        ("c", "c"),
        ("J\\", "ɟ"),
        ("J", "ɲ"),
        ("C", "ç"),
        ("j\\", "ʝ"),
        ("j", "j"),
        ("L", "ʎ"),
        ("L\\", "ʟ"),
        ("k", "k"),
        ("g", "ɡ"),
        ("N", "ŋ"),
        ("x", "x"),
        ("G", "ɣ"),
        ("M\\", "ɰ"),
        ("q", "q"),
        ("G\\", "ɢ"),
        ("N\\", "ɴ"),
        ("R\\", "ʀ"),
        ("X", "χ"),
        ("R", "ʁ"),
        ("X\\", "ħ"),
        ("?\\", "ʕ"),
        (">\\", "ʡ"),
        ("?", "ʔ"),
        ("h", "h"),
        ("h\\", "ɦ"),
        ("O\\", "ʘ"),
        ("|\\", "ǀ"),
        ("!\\", "ǃ"),
        ("=\\", "ǂ"),
        ("|\\|\\", "ǁ"),
        ("5", "l"),
        ("i", "i"),
        ("y", "y"),
        ("1", "ɨ"),
        ("}", "ʉ"),
        ("M", "ɯ"),
        ("u", "u"),
        ("I", "ɪ"),
        ("Y", "ʏ"),
        ("U", "ʊ"),
        ("e", "e"),
        ("2", "ø"),
        ("@\\", "ɘ"),
        ("8", "ɵ"),
        ("7", "ɤ"),
        ("o", "o"),
        ("@", "ə"),
        ("E", "ɛ"),
        ("9", "œ"),
        ("3", "ɜ"),
        ("3\\", "ɞ"),
        ("V", "ʌ"),
        ("O", "ɔ"),
        ("{", "æ"),
        ("6", "ɐ"),
        ("a", "a"),
        ("&", "ɶ"),
        ("A", "ɑ"),
        ("Q", "ɒ"),
    ]
}
