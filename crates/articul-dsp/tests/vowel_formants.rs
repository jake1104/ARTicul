use articul_phon::lookup;

fn f1f2(symbol: &str) -> (f32, f32) {
    let p = lookup(symbol).unwrap_or_else(|| panic!("{symbol} must resolve"));
    let (f1, f2, _) = articul_dsp::vowel_formants(&p).expect("vowel must have targets");
    (f1, f2)
}

fn within(v: f32, target: f32) -> bool {
    (v - target).abs() <= 0.15 * target
}

#[test]
fn pb_anchors_within_15_percent() {
    let cases = [
        ("i", 270.0, 2290.0),
        ("ɪ", 390.0, 1990.0),
        ("e", 530.0, 1840.0),
        ("ɛ", 660.0, 1720.0),
        ("æ", 660.0, 1720.0),
        ("ɑ", 730.0, 1090.0),
        ("ɔ", 570.0, 840.0),
        ("ʊ", 440.0, 1020.0),
        ("u", 300.0, 870.0),
        ("ʌ", 600.0, 1170.0),
    ];
    for (s, f1, f2) in cases {
        let (a, b) = f1f2(s);
        assert!(within(a, f1), "{s} F1={a} expected {f1}");
        assert!(within(b, f2), "{s} F2={b} expected {f2}");
    }
}

#[test]
fn all_vowels_have_targets_in_range() {
    let symbols = [
        "i", "y", "ɨ", "ʉ", "ɯ", "u", "ɪ", "ʏ", "ʊ", "e", "ø", "ɘ", "ɵ", "ɤ", "o", "ə", "ɛ", "œ",
        "ɜ", "ɞ", "ʌ", "ɔ", "æ", "ɐ", "a", "ɶ", "ɑ", "ɒ",
    ];
    assert_eq!(symbols.len(), 28);
    for s in symbols {
        let p = lookup(s).unwrap_or_else(|| panic!("{s} must resolve"));
        let (f1, f2, f3) = articul_dsp::vowel_formants(&p).expect("vowel target");
        assert!((200.0..=900.0).contains(&f1), "{s} F1={f1}");
        assert!((700.0..=2600.0).contains(&f2), "{s} F2={f2}");
        assert!((2000.0..=3200.0).contains(&f3), "{s} F3={f3}");
    }
}

#[test]
fn consonants_have_no_vowel_targets() {
    for s in ["p", "m", "s", "ʔ"] {
        let p = lookup(s).unwrap_or_else(|| panic!("{s} must resolve"));
        assert!(articul_dsp::vowel_formants(&p).is_none());
    }
}

#[test]
fn openness_raises_f1_and_frontness_raises_f2() {
    let (fi, _) = f1f2("i");
    let (fa, _) = f1f2("a");
    assert!(fa > fi);
    let (_, f2i) = f1f2("i");
    let (_, f2u) = f1f2("u");
    assert!(f2i > f2u);
}
