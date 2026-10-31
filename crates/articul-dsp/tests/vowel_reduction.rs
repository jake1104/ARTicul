use articul_dsp::reduced_vowel_targets;
use articul_dsp::vowel_formants;

fn lookup(x: &str) -> articul_phon::Phoneme {
    articul_phon::lookup(x).expect("symbol must resolve")
}

#[test]
fn unstressed_a_centralizes() {
    let (f1, f2, f3) = reduced_vowel_targets(&lookup("a"), false).expect("vowel");
    assert!((f1 - 667.0).abs() < 1.0, "f1={f1}");
    assert!((f2 - 1295.0).abs() < 1.0, "f2={f2}");
    assert!((f3 - 2640.0).abs() < 1.0, "f3={f3}");
}

#[test]
fn unstressed_i_centralizes() {
    let (f1, f2, f3) = reduced_vowel_targets(&lookup("i"), false).expect("vowel");
    assert!((f1 - 352.0).abs() < 1.0, "f1={f1}");
    assert!((f2 - 2030.0).abs() < 1.0, "f2={f2}");
    assert!((f3 - 2750.0).abs() < 1.0, "f3={f3}");
}

#[test]
fn stressed_vowel_keeps_full_targets() {
    let p = lookup("a");
    assert_eq!(reduced_vowel_targets(&p, true), vowel_formants(&p));
    assert!(vowel_formants(&p).is_some());
}

#[test]
fn consonant_has_no_reduced_targets() {
    let p = lookup("m");
    assert_eq!(reduced_vowel_targets(&p, false), None);
}
