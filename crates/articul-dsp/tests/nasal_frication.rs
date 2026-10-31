use articul_dsp::frication_noise;
use articul_dsp::nasalize_bandwidths;

#[test]
fn nasal_widens_bandwidth() {
    let out = nasalize_bandwidths(&[60.0, 90.0]);
    assert_eq!(out, vec![90.0, 135.0]);
}

#[test]
fn frication_silence_at_zero_level() {
    let out = frication_noise(256, 0.0);
    assert!(out.iter().all(|v| *v == 0.0));
}

#[test]
fn frication_noisy_at_positive_level() {
    let out = frication_noise(256, 0.5);
    assert!(out.iter().any(|v| v.abs() > 0.01));
}

#[test]
fn nasal_branch_needed_for_m_not_p() {
    let m = articul_phon::lookup("m").expect("m must resolve");
    let p = articul_phon::lookup("p").expect("p must resolve");
    assert!(articul_dsp::nasal_branch_needed(&m));
    assert!(!articul_dsp::nasal_branch_needed(&p));
}

#[test]
fn frication_level_boosted_for_voiceless_fricative() {
    let s = articul_phon::lookup("s").expect("s must resolve");
    let m = articul_phon::lookup("m").expect("m must resolve");
    assert!(articul_dsp::frication_level_for(&s, 0.1) > articul_dsp::frication_level_for(&m, 0.1));
}
