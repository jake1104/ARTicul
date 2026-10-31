#[test]
fn renders_fixed_sentence_to_expected_samples() {
    let samples = articul_cli::render_sentence("hi", 22050, 120.0);
    assert!(!samples.is_empty());
    assert!(samples.iter().all(|v| v.is_finite()));
    assert!(samples.iter().any(|v| v.abs() > 0.01));
}

#[test]
fn empty_text_gives_empty() {
    let samples = articul_cli::render_sentence("... !!!", 22050, 120.0);
    assert!(samples.is_empty());
}

#[test]
fn output_differs_per_text() {
    let a = articul_cli::render_sentence("hi", 22050, 120.0);
    let b = articul_cli::render_sentence("mam", 22050, 120.0);
    assert_ne!(a.len(), b.len());
}
