use articul_dsp::effective_aspiration;
use articul_phon::lookup;

#[test]
fn unaspirated_keeps_base_noise() {
    let p = lookup("p").expect("p must resolve");
    assert_eq!(effective_aspiration(&p, 0.05), 0.05);
}

#[test]
fn aspirated_boosts_noise() {
    let mut p = lookup("p").expect("p must resolve");
    p.secondary.aspirated = true;
    assert!(effective_aspiration(&p, 0.05) > 0.05);
}

#[test]
fn nasalized_vowel_does_not_boost_aspiration() {
    let i = lookup("i").expect("i must resolve");
    assert_eq!(effective_aspiration(&i, 0.05), 0.05);
}
