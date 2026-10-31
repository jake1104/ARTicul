use articul_phon::lookup;

#[test]
fn devoice_turns_b_to_voiceless_keeping_place_manner() {
    let b = lookup("b").expect("b must resolve");
    let out = articul_phon::devoice_obstruent(&b);
    assert!(!out.is_voiced());
    assert_eq!(out.place(), b.place());
    assert_eq!(out.manner(), b.manner());
}

#[test]
fn nasalize_marks_vowel_nasal() {
    let i = lookup("i").expect("i must resolve");
    let out = articul_phon::nasalize_vowel(&i);
    assert!(out.is_nasal());
}

#[test]
fn apply_rule_preserves_features_shape() {
    let b = lookup("b").expect("b must resolve");
    let out = articul_phon::apply_rule(&b);
    assert_eq!(out.place(), b.place());
    assert_eq!(out.manner(), b.manner());
}
