#[test]
fn render_is_deterministic_across_runs() {
    let a = articul_cli::render_sentence("hE \"loU", 22050, 120.0);
    let b = articul_cli::render_sentence("hE \"loU", 22050, 120.0);
    assert_eq!(a.len(), b.len());
    assert!(a.iter().zip(b.iter()).all(|(x, y)| x == y));
}

#[test]
fn glide_regions_stay_finite() {
    let out = articul_cli::render_sentence("oU asa", 22050, 120.0);
    assert!(!out.is_empty());
    assert!(out.iter().all(|v| v.is_finite()));
    assert!(out.iter().any(|v| v.abs() > 0.01));
}
