use articul_dsp::fricative_shaping;
use articul_dsp::ParallelFilter;

fn shaped_noise(xsampa: &str) -> Vec<f32> {
    let ipa = match xsampa {
        "S" => "ʃ",
        other => other,
    };
    let p = articul_phon::lookup(ipa).expect("symbol must resolve");
    let pairs = fricative_shaping(&p);
    let filt = ParallelFilter::from_pairs(&pairs, 22050);
    let noise = articul_dsp::frication_noise(4410, 0.3);
    filt.process(&noise)
}

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
fn sibilant_shaping_carries_more_high_frequency_than_weak() {
    let s = hp_rms(&shaped_noise("s"));
    let f = hp_rms(&shaped_noise("f"));
    assert!(s > 2.0 * f, "s={s} f={f}");
}

#[test]
fn voiced_pair_splits_the_same_way() {
    let z = hp_rms(&shaped_noise("z"));
    let v = hp_rms(&shaped_noise("v"));
    assert!(z > 2.0 * v, "z={z} v={v}");
}

#[test]
fn postalveolar_peak_sits_below_alveolar() {
    let s = hp_rms(&shaped_noise("s"));
    let sh = hp_rms(&shaped_noise("S"));
    assert!(s > sh, "s={s} S={sh}");
}
