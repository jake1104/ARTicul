#[test]
fn cpp_flag_consistent() {
    assert_eq!(articul_dsp::cpp_available(), cfg!(feature = "cpp"));
}

#[cfg(feature = "cpp")]
#[test]
fn cpp_matches_rust_single_resonator() {
    let input = unit_impulse(512);
    let rust = articul_dsp::CascadeFilter::single(500.0, 60.0, 22050).process(&input);
    let cpp = articul_dsp::cpp_process_single(500.0, 60.0, 22050, &input);
    assert_eq!(rust.len(), cpp.len());
    let mut worst: f32 = 0.0;
    for (x, y) in rust.iter().zip(cpp.iter()) {
        worst = worst.max((x - y).abs());
    }
    assert!(worst < 1e-5, "worst={worst}");
}

#[cfg(feature = "cpp")]
fn unit_impulse(n: usize) -> Vec<f32> {
    let mut v = vec![0.0; n];
    v[0] = 1.0;
    v
}
