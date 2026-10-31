use articul_dsp::nasal_notch;

fn lookup(x: &str) -> articul_phon::Phoneme {
    articul_phon::lookup(x).expect("symbol must resolve")
}

#[test]
fn nasal_consonant_gets_notch() {
    let (f0, bw) = nasal_notch(&lookup("m")).expect("nasal notch");
    assert!((f0 - 1000.0).abs() < 1.0, "notch at {f0}Hz");
    assert!(bw > 0.0, "bandwidth {bw}");
}

#[test]
fn oral_consonant_gets_none() {
    assert_eq!(nasal_notch(&lookup("p")), None);
    assert_eq!(nasal_notch(&lookup("b")), None);
}

#[test]
fn nasalized_vowel_gets_notch() {
    let mut v = articul_phon::lookup("a").expect("vowel");
    v.secondary.nasalized = true;
    assert!(nasal_notch(&v).is_some());
}

#[test]
fn plain_vowel_gets_none() {
    assert_eq!(nasal_notch(&lookup("a")), None);
}
