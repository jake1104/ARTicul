use articul_dsp::CascadeFilter;
use articul_dsp::ParallelFilter;

fn rms(x: &[f32]) -> f32 {
    (x.iter().map(|v| v * v).sum::<f32>() / x.len().max(1) as f32).sqrt()
}

fn sine(freq: f32, n: usize) -> Vec<f32> {
    (0..n)
        .map(|i| (2.0 * std::f32::consts::PI * freq * i as f32 / 22050.0).sin())
        .collect()
}

#[test]
fn step_matches_batched_process() {
    let tone = sine(700.0, 2205);
    let a = CascadeFilter::from_pairs(&[(700.0, 120.0), (1220.0, 150.0)], 22050).process(&tone);
    let mut f = CascadeFilter::from_pairs(&[(700.0, 120.0), (1220.0, 150.0)], 22050);
    let b: Vec<f32> = tone.iter().map(|s| f.step(*s)).collect();
    assert_eq!(a.len(), b.len());
    for (x, y) in a.iter().zip(b.iter()) {
        assert!((x - y).abs() < 1e-5);
    }
}

#[test]
fn retune_moves_resonance() {
    let tone = sine(1000.0, 2205);
    let f = CascadeFilter::from_pairs(&[(500.0, 120.0)], 22050);
    let before = rms(&f.process(&tone));
    let mut g = CascadeFilter::from_pairs(&[(500.0, 120.0)], 22050);
    g.retune(&[(1000.0, 120.0)], 22050);
    let after = rms(&g.process(&tone));
    assert!(after > 2.0 * before, "before={before} after={after}");
}

#[test]
fn parallel_retune_moves_resonance() {
    let tone = sine(6000.0, 2205);
    let f = ParallelFilter::from_pairs(&[(1500.0, 800.0, 0.5)], 22050);
    let before = rms(&f.process(&tone));
    let mut g = ParallelFilter::from_pairs(&[(1500.0, 800.0, 0.5)], 22050);
    g.retune(&[(6000.0, 500.0, 1.0)], 22050);
    let after = rms(&g.process(&tone));
    assert!(after > 2.0 * before, "before={before} after={after}");
}
