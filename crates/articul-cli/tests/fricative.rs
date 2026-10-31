fn hp_rms(x: &[f32]) -> f32 {
    let mut prev = 0.0f32;
    let mut acc = 0.0f32;
    for v in x {
        let y = *v - prev;
        prev = *v;
        acc += y * y;
    }
    (acc / x.len().max(1) as f32).sqrt()
}

#[test]
fn rendered_sibilant_exceeds_weak_fricative_up_high() {
    let s = articul_cli::render_sentence("s", 22050, 120.0);
    let f = articul_cli::render_sentence("f", 22050, 120.0);
    assert!(hp_rms(&s) > 1.5 * hp_rms(&f));
}

#[test]
fn rendered_voiced_pair_splits_up_high() {
    let z = articul_cli::render_sentence("z", 22050, 120.0);
    let v = articul_cli::render_sentence("v", 22050, 120.0);
    assert!(hp_rms(&z) > 1.5 * hp_rms(&v));
}
