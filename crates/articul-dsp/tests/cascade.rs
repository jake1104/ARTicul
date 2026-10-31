use articul_dsp::CascadeFilter;

#[test]
fn cascade_preserves_length_and_stays_finite() {
    let f = CascadeFilter::single(500.0, 60.0, 22050);
    let imp = unit_impulse(512);
    let out = f.process(&imp);
    assert_eq!(out.len(), 512);
    assert!(out.iter().all(|v| v.is_finite()));
}

#[test]
fn single_resonator_prefers_its_formant() {
    let f = CascadeFilter::single(500.0, 60.0, 22050);
    let on = sine(500.0, 0.2, 22050);
    let off = sine(1500.0, 0.2, 22050);
    assert!(rms(&f.process(&on)) > rms(&f.process(&off)));
}

#[test]
fn impulse_response_decays() {
    let f = CascadeFilter::single(500.0, 60.0, 22050);
    let out = f.process(&unit_impulse(2205));
    let tail: f32 = out[1102..].iter().map(|v| v.abs()).sum::<f32>() / 1103.0;
    assert!(tail < 0.01, "tail={tail}");
}

fn unit_impulse(n: usize) -> Vec<f32> {
    let mut v = vec![0.0; n];
    v[0] = 1.0;
    v
}

fn sine(freq: f32, secs: f32, sr: u32) -> Vec<f32> {
    let n = (secs * sr as f32) as usize;
    (0..n)
        .map(|i| (2.0 * std::f32::consts::PI * freq * i as f32 / sr as f32).sin())
        .collect()
}

fn rms(x: &[f32]) -> f32 {
    (x.iter().map(|v| v * v).sum::<f32>() / x.len() as f32).sqrt()
}
