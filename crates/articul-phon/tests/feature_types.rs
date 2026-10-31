use articul_phon::Phoneme;

#[test]
fn pulmonic_p_is_voiceless_bilabial_plosive() {
    let p = Phoneme::voiceless_consonant(
        'p',
        articul_phon::Place::Bilabial,
        articul_phon::Manner::Plosive,
    );
    assert_eq!(p.place(), Some(articul_phon::Place::Bilabial));
    assert_eq!(p.manner(), Some(articul_phon::Manner::Plosive));
    assert!(!p.is_voiced());
    assert!(!p.is_nasal());
}

#[test]
fn nasal_m_is_voiced_nasal() {
    let m = Phoneme::voiced_consonant(
        'm',
        articul_phon::Place::Bilabial,
        articul_phon::Manner::Nasal,
    );
    assert!(m.is_voiced());
    assert!(m.is_nasal());
}

#[test]
fn vowel_i_has_close_front_unrounded() {
    let v = Phoneme::vowel(
        'i',
        articul_phon::VowelHeight::Close,
        articul_phon::VowelBackness::Front,
        false,
    );
    assert_eq!(v.place(), None);
    assert_eq!(v.manner(), None);
    assert!(!v.is_nasal());
}
