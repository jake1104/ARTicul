use articul_front::plan_utterance;

fn planned_lens(word: &str, sample_rate: u32) -> Vec<usize> {
    let words = vec![word.to_string()];
    let parsed = articul_front::parse_utterance(&words);
    plan_utterance(&parsed, 1.0, 1.0, 120.0)
        .iter()
        .map(|u| {
            ((u.duration_ms as f32 / 1000.0) * sample_rate as f32)
                .round()
                .max(1.0) as usize
        })
        .collect()
}

#[test]
fn vv_boundary_gets_long_glide_crossfade() {
    let out = articul_cli::render_sentence("oU", 22050, 120.0);
    let lens = planned_lens("oU", 22050);
    assert_eq!(lens.len(), 2);
    assert_eq!(out.len(), lens[0] + lens[1] - 1102);
}

#[test]
fn consonant_boundary_keeps_short_crossfade() {
    let out = articul_cli::render_sentence("ot", 22050, 120.0);
    let lens = planned_lens("ot", 22050);
    assert_eq!(lens.len(), 2);
    assert_eq!(out.len(), lens[0] + lens[1] - 176);
}
