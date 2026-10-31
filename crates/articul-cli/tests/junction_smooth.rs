use articul_front::parse_utterance;
use articul_front::plan_utterance;
use articul_front::prosody::ProsodicPhoneme;

const SR: u32 = 22050;

fn is_vowel_unit(u: &ProsodicPhoneme) -> bool {
    matches!(u.phoneme.kind, articul_phon::SegmentKind::Vowel { .. })
}

fn is_goat_onset(u: &ProsodicPhoneme) -> bool {
    !u.is_pause
        && u.stress != articul_front::Stress::Unstressed
        && u.phoneme.base_symbol == "o"
        && matches!(
            u.phoneme.kind,
            articul_phon::SegmentKind::Vowel { rounded: true, .. }
        )
}

fn is_goat_offglide(u: &ProsodicPhoneme) -> bool {
    !u.is_pause
        && u.stress == articul_front::Stress::Unstressed
        && u.phoneme.base_symbol == "\u{028A}"
        && matches!(u.phoneme.kind, articul_phon::SegmentKind::Vowel { .. })
}

fn work_groups(planned: &[ProsodicPhoneme]) -> Vec<Vec<usize>> {
    let mut groups: Vec<Vec<usize>> = Vec::new();
    let mut i = 0usize;
    while i < planned.len() {
        if i + 1 < planned.len() && is_goat_onset(&planned[i]) && is_goat_offglide(&planned[i + 1])
        {
            groups.push(vec![i, i + 1]);
            i += 2;
        } else {
            groups.push(vec![i]);
            i += 1;
        }
    }
    groups
}

fn group_len_ms(planned: &[ProsodicPhoneme], group: &[usize]) -> u32 {
    group.iter().map(|oi| planned[*oi].duration_ms).sum()
}

fn samples(ms: u32) -> usize {
    ((ms as f32 / 1000.0) * SR as f32).round().max(1.0) as usize
}

fn rms(x: &[f32]) -> f32 {
    (x.iter().map(|v| v * v).sum::<f32>() / x.len().max(1) as f32).sqrt()
}

fn window_step_db(track: &[f32], center: usize) -> f32 {
    let w = (SR as f32 * 0.010) as usize;
    let left = &track[center - w..center];
    let right = &track[center..center + w];
    20.0 * (rms(right) / rms(left).max(1e-9)).log10()
}

#[test]
fn boundary_gain_step_bounded() {
    let inputs = ["hE \"loU", "%an njVN \"hasejo", "%jV\"bo%se%jo"];
    let mut total_count = 0usize;
    let mut worst = 0.0f32;
    let mut worst_at = String::new();
    let mut report = String::new();
    for text in inputs {
        let words: Vec<String> = articul_front::normalize(text);
        let parsed = parse_utterance(&words);
        let planned = plan_utterance(&parsed, 1.0, 1.0, 120.0);
        let out = articul_cli::render_sentence(text, SR, 120.0);
        let track = articul_cli::render_gain_track(text, SR, 120.0);
        assert!(!out.is_empty());
        assert_eq!(
            track.len(),
            out.len(),
            "gain track length must match audio length for {text}"
        );
        let groups = work_groups(&planned);
        let lens: Vec<usize> = groups
            .iter()
            .map(|g| samples(group_len_ms(&planned, g)))
            .collect();
        let total = planned.len();
        let mut pos = 0usize;
        for (gi, group) in groups.iter().enumerate() {
            let fade = if gi == 0 {
                0usize
            } else {
                let left_v = is_vowel_unit(&planned[groups[gi - 1][0]]);
                let right_v = is_vowel_unit(&planned[group[0]]);
                if left_v && right_v {
                    1102usize
                } else {
                    176usize
                }
            };
            if gi > 0 {
                pos -= fade.min(pos);
            }
            if gi > 0 {
                total_count += 1;
                let center = pos + fade / 2;
                let step = window_step_db(&track, center);
                let la = groups[gi - 1].last().copied().unwrap_or(0);
                let rb = group[0];
                let left_edge = articul_cli::segment_gain_db(&planned[la], la, total);
                let right_edge = articul_cli::segment_gain_db(&planned[rb], rb, total);
                let table_step = (right_edge - left_edge).abs();
                if step.abs() > worst {
                    worst = step.abs();
                    worst_at = format!("{text} boundary {total_count}");
                }
                report.push_str(&format!(
                    "{text} b{total_count} center={center} table_step={table_step:.1}dB track_step={step:.2}dB\n"
                ));
            }
            pos += lens[gi];
        }
    }
    assert_eq!(
        total_count, 21,
        "expected 21 inter-segment boundaries\n{report}"
    );
    assert!(
        worst <= 5.0,
        "max boundary gain step {worst:.2}dB at {worst_at} exceeds 5.0dB\n{report}"
    );
}
