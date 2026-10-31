use articul_phon::lookup;
use articul_phon::Manner;
use articul_phon::Place;

#[test]
fn lookup_pulmonic_samples() {
    let p = lookup("p").expect("p must resolve");
    assert_eq!(p.place(), Some(Place::Bilabial));
    assert_eq!(p.manner(), Some(Manner::Plosive));
    assert!(!p.is_voiced());
    let m = lookup("m").expect("m must resolve");
    assert!(m.is_voiced());
    assert!(m.is_nasal());
}

#[test]
fn lookup_vowel_samples() {
    let i = lookup("i").expect("i must resolve");
    assert_eq!(i.place(), None);
    assert_eq!(i.manner(), None);
}

#[test]
fn lookup_nonpulmonic_samples() {
    assert!(lookup("ʘ").is_some());
    assert!(lookup("ɓ").is_some());
    assert!(lookup("pʼ").is_some());
}

#[test]
fn lookup_extipa_samples() {
    assert!(lookup("ʬ").is_some());
}

#[test]
fn lookup_unknown_returns_none() {
    assert!(lookup("?").is_none());
}

#[test]
fn lookup_all_pulmonic_inventory() {
    let symbols = [
        "p", "b", "m", "ʙ", "ɸ", "β", "ɱ", "ⱱ", "f", "v", "ʋ", "θ", "ð", "t", "d", "n", "r", "ɾ",
        "s", "z", "ɬ", "ɮ", "ɹ", "l", "ʃ", "ʒ", "ʈ", "ɖ", "ɳ", "ʂ", "ʐ", "ɻ", "ɭ", "ɽ", "c", "ɟ",
        "ɲ", "ç", "ʝ", "j", "ʎ", "k", "ɡ", "ŋ", "x", "ɣ", "ɰ", "ʟ", "q", "ɢ", "ɴ", "ʀ", "χ", "ʁ",
        "ħ", "ʕ", "ʡ", "ʔ", "h", "ɦ",
    ];
    for s in symbols {
        assert!(lookup(s).is_some(), "missing {s}");
    }
}

#[test]
fn lookup_all_vowel_inventory() {
    let symbols = [
        "i", "y", "ɨ", "ʉ", "ɯ", "u", "ɪ", "ʏ", "ʊ", "e", "ø", "ɘ", "ɵ", "ɤ", "o", "ə", "ɛ", "œ",
        "ɜ", "ɞ", "ʌ", "ɔ", "æ", "ɐ", "a", "ɶ", "ɑ", "ɒ",
    ];
    for s in symbols {
        assert!(lookup(s).is_some(), "missing {s}");
    }
}
