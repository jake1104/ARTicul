use articul_front::Xsampa;
use articul_phon::LengthMark;

fn xs() -> Xsampa {
    Xsampa::new()
}

#[test]
fn lower_letters_match_ipa() {
    let (out, _) = xs().transcribe("pin");
    assert_eq!(out.len(), 3);
    assert_eq!(out[0].place(), Some(articul_phon::Place::Bilabial));
    assert_eq!(out[2].manner(), Some(articul_phon::Manner::Nasal));
}

#[test]
fn upper_letters_are_distinct_phonemes() {
    let (s, _) = xs().transcribe("S");
    assert_eq!(s.len(), 1);
    assert_eq!(s[0].place(), Some(articul_phon::Place::Postalveolar));
    let (n, _) = xs().transcribe("N");
    assert_eq!(n[0].manner(), Some(articul_phon::Manner::Nasal));
    assert_eq!(n[0].place(), Some(articul_phon::Place::Velar));
    let (t, _) = xs().transcribe("T");
    assert_eq!(t[0].place(), Some(articul_phon::Place::Dental));
}

#[test]
fn question_mark_is_glottal_stop() {
    let (out, _) = xs().transcribe("?");
    assert_eq!(out.len(), 1);
    assert_eq!(out[0].manner(), Some(articul_phon::Manner::Plosive));
    assert_eq!(out[0].place(), Some(articul_phon::Place::Glottal));
}

#[test]
fn backslash_forms_resolve() {
    let (click, _) = xs().transcribe("O\\");
    assert_eq!(click[0].manner(), Some(articul_phon::Manner::Click));
    let (retro, _) = xs().transcribe("t`");
    assert_eq!(retro[0].place(), Some(articul_phon::Place::Retroflex));
}

#[test]
fn aspiration_suffix_sets_flag() {
    let (out, _) = xs().transcribe("p_h");
    assert_eq!(out.len(), 1);
    assert!(out[0].secondary.aspirated);
    assert!(!out[0].is_nasal());
}

#[test]
fn nasal_suffix_marks_nasal() {
    let (out, _) = xs().transcribe("a~");
    assert_eq!(out.len(), 1);
    assert!(out[0].is_nasal());
}

#[test]
fn length_mark_sets_long() {
    let (out, _) = xs().transcribe("a:");
    assert_eq!(out.len(), 1);
    assert_eq!(out[0].duration.phonemic_length, LengthMark::Long);
}

#[test]
fn implosive_suffix_resolves() {
    let (out, _) = xs().transcribe("b_<");
    assert_eq!(out.len(), 1);
    assert_eq!(out[0].manner(), Some(articul_phon::Manner::Implosive));
}

#[test]
fn ejective_suffix_resolves() {
    let (out, _) = xs().transcribe("p_>");
    assert_eq!(out.len(), 1);
    assert_eq!(out[0].manner(), Some(articul_phon::Manner::Ejective));
}

#[test]
fn dental_suffix_shifts_place() {
    let (out, _) = xs().transcribe("t_d");
    assert_eq!(out.len(), 1);
    assert_eq!(out[0].place(), Some(articul_phon::Place::Dental));
}

#[test]
fn table_is_replaceable() {
    let g = Xsampa::with_table(vec![("q", "i")]);
    let (out, _) = g.transcribe("q");
    assert_eq!(out.len(), 1);
    assert_eq!(out[0].place(), None);
}

#[test]
fn skips_unknown_chars() {
    assert!(xs().transcribe("w").0.is_empty());
    assert_eq!(xs().transcribe("a$").0.len(), 1);
}
