use articul_front::parse_utterance;
use articul_front::plan_utterance;

fn is_vowel(p: &articul_phon::Phoneme) -> bool {
    matches!(p.kind, articul_phon::SegmentKind::Vowel { .. })
}

fn starts_of(planned: &[articul_front::prosody::ProsodicPhoneme], sample_rate: u32) -> Vec<usize> {
    let mut starts = Vec::with_capacity(planned.len());
    let mut pos = 0usize;
    for (i, u) in planned.iter().enumerate() {
        if i > 0 {
            let fade = if is_vowel(&planned[i - 1].phoneme) && is_vowel(&u.phoneme) {
                1102
            } else {
                176
            };
            pos -= fade.min(pos);
        }
        starts.push(pos);
        pos += ((u.duration_ms as f32 / 1000.0) * sample_rate as f32).round() as usize;
    }
    starts
}

#[test]
fn pause_region_renders_silence() {
    let words = vec!["a,".to_string(), "pa".to_string()];
    let parsed = parse_utterance(&words);
    let planned = plan_utterance(&parsed, 1.0, 1.0, 120.0);
    assert!(planned[1].is_pause);
    let out = articul_cli::render_planned(&planned, 22050);
    let starts = starts_of(&planned, 22050);
    let span = planned[1].duration_ms as usize * 22050 / 1000;
    let (ps, pe) = (starts[1] + 1200, starts[1] + span.saturating_sub(1200));
    let seg = &out[ps.min(out.len())..pe.min(out.len())];
    let rms = (seg.iter().map(|v| v * v).sum::<f32>() / seg.len().max(1) as f32).sqrt();
    assert!(rms < 0.02, "pause rms={rms}");
}

#[test]
fn pause_extends_utterance_by_its_own_length() {
    let plain = articul_cli::render_sentence("a pa", 22050, 120.0);
    let comma = articul_cli::render_sentence("a, pa", 22050, 120.0);
    let growth = comma.len() as isize - plain.len() as isize;
    assert!(growth > 1500 && growth < 3528, "growth={growth}");
}
