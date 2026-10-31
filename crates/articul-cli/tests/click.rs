use articul_front::parse_utterance;
use articul_front::plan_utterance;

fn segment_bounds(words: &[String], sample_rate: u32) -> Vec<(usize, usize)> {
    let parsed = parse_utterance(words);
    let planned = plan_utterance(&parsed, 1.0, 1.0, 120.0);
    let mut vowels: Vec<bool> = Vec::new();
    for w in &parsed {
        for p in &w.phonemes {
            vowels.push(matches!(p.kind, articul_phon::SegmentKind::Vowel { .. }));
        }
    }
    let mut bounds = Vec::with_capacity(planned.len());
    let mut pos = 0usize;
    for (i, u) in planned.iter().enumerate() {
        if i > 0 {
            let fade = if vowels[i - 1] && vowels[i] {
                1102
            } else {
                176
            };
            pos -= fade.min(pos);
        }
        let len = ((u.duration_ms as f32 / 1000.0) * sample_rate as f32)
            .round()
            .max(1.0) as usize;
        bounds.push((pos, pos + len));
        pos += len;
    }
    bounds
}

fn max_jump(x: &[f32], from: usize, to: usize) -> f32 {
    let to = to.min(x.len().saturating_sub(1));
    let mut m = 0.0f32;
    for i in from.min(to)..to {
        m = m.max((x[i + 1] - x[i]).abs());
    }
    m
}

#[test]
fn fricative_plosive_junction_stays_within_content() {
    let words = vec!["TIs".to_string(), "TIN".to_string()];
    let out = articul_cli::render_sentence("TIs TIN", 22050, 120.0);
    let bounds = segment_bounds(&words, 22050);
    assert_eq!(bounds.len(), 6);
    let (s_start, s_end) = bounds[2];
    let junction = bounds[3].0;
    let interior = max_jump(&out, s_start + 200, s_end.saturating_sub(200));
    let edge = max_jump(&out, junction.saturating_sub(50), junction + 50);
    assert!(
        edge <= 1.5 * interior.max(0.05),
        "junction {edge:.3} vs interior {interior:.3}"
    );
}
