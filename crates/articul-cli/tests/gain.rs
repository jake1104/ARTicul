use articul_front::plan;
use articul_front::prosody::ProsodicPhoneme;
use articul_front::Stress;
use articul_front::Xsampa;

fn unit(symbol: &str, stress: Stress) -> ProsodicPhoneme {
    let p = articul_phon::lookup(symbol).expect("symbol must resolve");
    let out = plan(
        std::slice::from_ref(&p),
        std::slice::from_ref(&stress),
        1.0,
        1.0,
        120.0,
    );
    assert_eq!(out.len(), 1);
    out.into_iter().next().unwrap()
}

fn approx(actual: f32, expected: f32) {
    assert!(
        (actual - expected).abs() < 1e-4,
        "got {actual}, want {expected}"
    );
}

#[test]
fn stressed_vowel_at_reference_zero_db() {
    let u = unit("a", Stress::Primary);
    approx(articul_cli::segment_gain_db(&u, 0, 3), 0.0);
}

#[test]
fn unstressed_vowel_minus_3_5_db() {
    let u = unit("a", Stress::Unstressed);
    approx(articul_cli::segment_gain_db(&u, 0, 3), -1.75);
}

#[test]
fn nasal_minus_8_db() {
    let u = unit("m", Stress::Unstressed);
    approx(articul_cli::segment_gain_db(&u, 0, 3), -4.0);
}

#[test]
fn sonorant_minus_7_db() {
    let u = unit("l", Stress::Unstressed);
    approx(articul_cli::segment_gain_db(&u, 0, 3), -3.5);
}

#[test]
fn sibilant_minus_5_db() {
    let u = unit("s", Stress::Unstressed);
    approx(articul_cli::segment_gain_db(&u, 0, 3), -2.5);
}

#[test]
fn weak_fricative_floored_at_minus_12_db() {
    let u = unit("f", Stress::Unstressed);
    approx(articul_cli::segment_gain_db(&u, 0, 3), -6.0);
}

#[test]
fn voiced_sibilant_floored_at_minus_12_db() {
    let u = unit("z", Stress::Unstressed);
    approx(articul_cli::segment_gain_db(&u, 0, 3), -6.0);
}

#[test]
fn voiced_weak_fricative_floored_at_minus_12_db() {
    let u = unit("v", Stress::Unstressed);
    approx(articul_cli::segment_gain_db(&u, 0, 3), -6.0);
}

#[test]
fn default_plosive_zero_db() {
    let u = unit("t", Stress::Unstressed);
    approx(articul_cli::segment_gain_db(&u, 0, 2), 0.0);
}

#[test]
fn unstressed_consonant_ignores_stress() {
    let plain = unit("t", Stress::Unstressed);
    let marked = unit("t", Stress::Primary);
    approx(
        articul_cli::segment_gain_db(&plain, 0, 2),
        articul_cli::segment_gain_db(&marked, 0, 2),
    );
}

#[test]
fn aspirated_floor_minus_3_db() {
    let g = Xsampa::new();
    let (seq, marks) = g.transcribe("h_h");
    assert_eq!(seq.len(), 1);
    let out = plan(&seq, &marks, 1.0, 1.0, 120.0);
    assert!(out[0].phoneme.secondary.aspirated);
    approx(articul_cli::segment_gain_db(&out[0], 0, 3), -1.5);
}

#[test]
fn declination_per_segment() {
    let u = unit("a", Stress::Unstressed);
    approx(articul_cli::segment_gain_db(&u, 2, 10), -2.75);
}

#[test]
fn declination_caps_at_12_db() {
    let u = unit("a", Stress::Unstressed);
    approx(articul_cli::segment_gain_db(&u, 20, 30), -6.0);
}

#[test]
fn final_consonant_extra_minus_4_db() {
    let u = unit("t", Stress::Unstressed);
    approx(articul_cli::segment_gain_db(&u, 4, 5), -4.0);
}

#[test]
fn final_vowel_skips_extra_minus_4_db() {
    let u = unit("a", Stress::Unstressed);
    approx(articul_cli::segment_gain_db(&u, 4, 5), -3.75);
}

fn rms(x: &[f32]) -> f32 {
    (x.iter().map(|v| v * v).sum::<f32>() / x.len().max(1) as f32).sqrt()
}

#[test]
fn stressed_vowel_louder_than_unstressed() {
    let word = "apa";
    let marks = vec![Stress::Primary, Stress::Unstressed, Stress::Unstressed];
    let (seq, _) = Xsampa::new().transcribe(word);
    assert_eq!(seq.len(), marks.len());
    let planned = plan(&seq, &marks, 1.0, 1.0, 120.0);
    let out = articul_cli::render_planned(&planned, 22050);
    let mut starts = Vec::with_capacity(planned.len() + 1);
    let mut pos = 0usize;
    for (idx, u) in planned.iter().enumerate() {
        if idx > 0 {
            let f = 176usize;
            pos -= f.min(pos);
        }
        starts.push(pos);
        pos += ((u.duration_ms as f32 / 1000.0) * 22050.0).round() as usize;
    }
    let w0 = &out[starts[0] + 500..starts[0] + 1500];
    let w2 = &out[starts[2] + 300..starts[2] + 1300];
    let ratio = rms(w0) / rms(w2).max(1e-9);
    assert!(ratio > 1.8, "ratio={ratio}");
}

#[test]
fn fricative_onset_ramps_up() {
    let out = articul_cli::render_sentence("s", 22050, 120.0);
    let q = out.len() / 4;
    assert!(rms(&out[..q]) < rms(&out[3 * q..]));
}

#[test]
fn burst_decay_for_unvoiced_plosive() {
    let out = articul_cli::render_sentence("t", 22050, 120.0);
    assert!(out.len() > 660);
    let first = rms(&out[..330]);
    let last = rms(&out[out.len() - 330..]);
    assert!(first > last, "first={first} last={last}");
}

#[test]
fn final_fade_quiets_ending() {
    let out = articul_cli::render_sentence("a", 22050, 120.0);
    let tenth = (out.len() / 10).max(1);
    let first = out[..tenth].iter().map(|v| v.abs()).fold(0.0, f32::max);
    let last = out[out.len() - tenth..]
        .iter()
        .map(|v| v.abs())
        .fold(0.0, f32::max);
    assert!(last < 0.5 * first, "last={last} first={first}");
}
