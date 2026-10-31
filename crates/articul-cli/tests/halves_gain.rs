use articul_front::parse_utterance;
use articul_front::plan_utterance;

fn rms_db(x: &[f32]) -> f32 {
    let r = (x.iter().map(|v| v * v).sum::<f32>() / x.len().max(1) as f32).sqrt();
    20.0 * r.max(1e-9).log10()
}

fn is_vowel(p: &articul_phon::Phoneme) -> bool {
    matches!(p.kind, articul_phon::SegmentKind::Vowel { .. })
}

fn segment_starts(lens: &[usize], fades: &[usize]) -> Vec<usize> {
    let mut starts = vec![0usize; lens.len()];
    for i in 1..lens.len() {
        starts[i] = starts[i - 1] + lens[i - 1] - fades[i];
    }
    starts
}

fn render_hello() -> Vec<f32> {
    articul_cli::render_sentence("hE \"loU", 22050, 120.0)
}

const MAX_HALVES_DIFF_DB: f32 = 5.0;
const MIN_SECOND_HALF_DBFS: f32 = -32.0;

#[test]
fn hello_halves_within_5db() {
    let out = render_hello();
    assert!(!out.is_empty());
    let n = out.len();
    let db0 = rms_db(&out[..n / 2]);
    let db1 = rms_db(&out[n / 2..]);
    assert!(
        (db1 - db0).abs() <= MAX_HALVES_DIFF_DB,
        "halves {db0:.2}dB vs {db1:.2}dB diff={:.2}dB",
        db1 - db0
    );
    assert!(
        db1 > MIN_SECOND_HALF_DBFS,
        "second half {db1:.2}dBFS below floor {MIN_SECOND_HALF_DBFS:.1}dBFS"
    );
}

#[test]
fn lateral_window_within_8db_of_stressed_vowel() {
    let sr = 22050u32;
    let out = render_hello();
    let n = out.len();
    let words = vec!["hE".to_string(), "\"loU".to_string()];
    let parsed = parse_utterance(&words);
    let planned = plan_utterance(&parsed, 1.0, 1.0, 120.0);
    let total = planned.len();
    let lens: Vec<usize> = planned
        .iter()
        .map(|u| {
            ((u.duration_ms as f32 / 1000.0) * sr as f32)
                .round()
                .max(1.0) as usize
        })
        .collect();
    let mut fades = vec![0usize; total];
    for i in 1..total {
        let pv = is_vowel(&planned[i - 1].phoneme);
        let cv = is_vowel(&planned[i].phoneme);
        fades[i] = if pv && cv { 1102 } else { 176 };
    }
    let starts = segment_starts(&lens, &fades);
    let li = planned
        .iter()
        .position(|u| {
            matches!(
                u.phoneme.manner(),
                Some(
                    articul_phon::Manner::Approximant
                        | articul_phon::Manner::LateralApproximant
                        | articul_phon::Manner::Trill
                        | articul_phon::Manner::TapFlap
                )
            )
        })
        .expect("lateral segment present");
    let oi = planned
        .iter()
        .position(|u| is_vowel(&u.phoneme) && u.stress != articul_front::Stress::Unstressed)
        .expect("stressed vowel present");
    let margin = 110usize;
    let next_fade = |i: usize| if i + 1 < total { fades[i + 1] } else { 0 };
    let ws = starts[li] + fades[li] + margin;
    let we = (starts[li] + lens[li] - next_fade(li) - margin).min(n);
    let vs = starts[oi] + fades[oi] + margin;
    let ve = (starts[oi] + lens[oi] - next_fade(oi) - margin).min(n);
    let ldb = rms_db(&out[ws..we]);
    let odb = rms_db(&out[vs..ve]);
    assert!(
        odb - ldb < 8.0,
        "lateral {ldb:.2}dB vs stressed vowel {odb:.2}dB gap={:.2}dB",
        odb - ldb
    );
}
