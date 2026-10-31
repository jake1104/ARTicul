use articul_dsp::locus_adjusted_formants;

fn lookup(x: &str) -> articul_phon::Phoneme {
    articul_phon::lookup(x).expect("symbol must resolve")
}

#[test]
fn alveolar_pulls_f2_up() {
    let plain = articul_dsp::vowel_formants(&lookup("a")).expect("vowel");
    let (_, plain_f2, _) = plain;
    let (_, pulled_f2, _) = locus_adjusted_formants(&lookup("a"), &lookup("t")).expect("adj");
    assert!(pulled_f2 > plain_f2, "plain={plain_f2} pulled={pulled_f2}");
    assert!((pulled_f2 - 1800.0).abs() < (plain_f2 - 1800.0).abs());
}

#[test]
fn labial_pulls_f2_down() {
    let (_, plain_f2, _) = articul_dsp::vowel_formants(&lookup("i")).expect("vowel");
    let (_, pulled_f2, _) = locus_adjusted_formants(&lookup("i"), &lookup("p")).expect("adj");
    assert!(pulled_f2 < plain_f2, "plain={plain_f2} pulled={pulled_f2}");
}

#[test]
fn velar_raises_f2_and_pinches_f3() {
    let (f1, f2, f3) = articul_dsp::vowel_formants(&lookup("a")).expect("vowel");
    let (g1, g2, g3) = locus_adjusted_formants(&lookup("a"), &lookup("k")).expect("adj");
    assert!((g1 - f1).abs() < 60.0, "f1 must barely move");
    assert!(g2 > f2, "f2 {f2} -> {g2}");
    assert!(
        (g3 - 2600.0).abs() < (f3 - 2600.0).abs(),
        "f3 must pinch toward 2600: {f3} -> {g3}"
    );
}

#[test]
fn non_neighbor_leaves_targets_alone() {
    let plain = articul_dsp::vowel_formants(&lookup("a")).expect("vowel");
    let same = locus_adjusted_formants(&lookup("a"), &lookup("a")).expect("adj");
    assert_eq!(plain, same);
}

fn slope_to(place: articul_phon::Place) -> f32 {
    let (_, lo, _) = articul_dsp::locus_pull_toward(0.0, 1000.0, 2500.0, place);
    let (_, hi, _) = articul_dsp::locus_pull_toward(0.0, 2000.0, 2500.0, place);
    (hi - lo) / 1000.0
}

#[test]
fn labial_slope_is_steep() {
    use articul_phon::Place;
    let k = slope_to(Place::Bilabial);
    assert!((k - 0.7).abs() < 0.05, "k={k}");
}

#[test]
fn alveolar_slope_is_flat() {
    use articul_phon::Place;
    let k = slope_to(Place::Alveolar);
    assert!((k - 0.3).abs() < 0.05, "k={k}");
}

#[test]
fn velar_slope_is_middle() {
    use articul_phon::Place;
    let k = slope_to(Place::Velar);
    assert!((k - 0.5).abs() < 0.05, "k={k}");
}
