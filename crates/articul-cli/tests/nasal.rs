fn dft_mag(x: &[f32], freq: f32, sample_rate: u32) -> f32 {
    let n = x.len();
    let (mut re, mut im) = (0.0f32, 0.0f32);
    for (i, v) in x.iter().enumerate() {
        let w = 0.5 - 0.5 * (std::f32::consts::PI * 2.0 * i as f32 / n.max(2) as f32).cos();
        let ph = 2.0 * std::f32::consts::PI * freq * i as f32 / sample_rate as f32;
        re += v * w * ph.cos();
        im -= v * w * ph.sin();
    }
    (re * re + im * im).sqrt() / n.max(1) as f32
}

fn band_dip(out: &[f32]) -> f32 {
    let n = out.len();
    let seg = &out[n / 4..n * 3 / 4];
    let e850 = dft_mag(seg, 850.0, 22050);
    let e1000 = dft_mag(seg, 1000.0, 22050);
    let e1150 = dft_mag(seg, 1150.0, 22050);
    e1000 / e850.max(e1150).max(1e-9)
}

#[test]
fn nasal_zero_dips_harder_than_oral() {
    let m = articul_cli::render_sentence("\"m:", 22050, 120.0);
    let b = articul_cli::render_sentence("\"b:", 22050, 120.0);
    let dip_m = band_dip(&m);
    let dip_b = band_dip(&b);
    assert!(dip_m < 0.5 * dip_b, "m {dip_m} vs b {dip_b}");
}

fn f2_band(x: &[f32]) -> f32 {
    let n = x.len();
    let seg = &x[n / 4..n * 3 / 4];
    dft_mag(seg, 1500.0, 22050)
}

#[test]
fn alveolar_context_lifts_f2_over_labial() {
    let ada = articul_cli::render_sentence("ada", 22050, 120.0);
    let aba = articul_cli::render_sentence("aba", 22050, 120.0);
    assert!(f2_band(&ada) > 1.05 * f2_band(&aba));
}
